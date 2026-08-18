from typing import Callable, List, Optional
from fastapi import Depends, Header, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.exceptions import AuthenticationException, PermissionDeniedException
from app.core.permissions import PermissionCode, RoleCode
from app.core.rate_limit import RateLimiter, login_rate_limiter, broadcast_rate_limiter, rate_limiter
from app.core.security import decode_access_token
from app.models.user import User
from app.repositories.user_repo import UserRepository

security_scheme = HTTPBearer(auto_error=False)


async def check_rate_limit(request: Request) -> None:
    """Rate limit dependency checking client IP."""
    await rate_limiter.check_rate_limit(request)


async def check_login_rate_limit(request: Request) -> None:
    """Rate limit specifically for login endpoint."""
    await login_rate_limiter.check_rate_limit(request)


async def check_broadcast_rate_limit(request: Request) -> None:
    """Rate limit specifically for broadcast send endpoint."""
    await broadcast_rate_limiter.check_rate_limit(request)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Validates JWT access token and returns authenticated active user."""
    if not credentials or not credentials.credentials:
        raise AuthenticationException("Missing or invalid Authorization header.")

    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload:
        raise AuthenticationException("Access token is invalid, expired, or malformed.")

    user_id = payload.get("sub")
    if not user_id:
        raise AuthenticationException("Token subject claim is missing.")

    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)
    if not user:
        # Fallback to get_with_roles if available
        if hasattr(user_repo, "get_with_roles"):
            user = await user_repo.get_with_roles(user_id)

    if not user:
        raise AuthenticationException("User account associated with token no longer exists.")

    if not user.is_active:
        raise AuthenticationException("User account is deactivated.")

    # Cache user on request state for audit logs
    request.state.current_user = user
    return user


async def get_optional_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """Optionally returns current user if valid bearer token is present."""
    if not credentials or not credentials.credentials:
        return None
    try:
        return await get_current_user(request, credentials, db)
    except Exception:
        return None


def require_roles(allowed_roles: List[str]) -> Callable:
    """Dependency factory checking that current user has one of the allowed roles (superadmin, admin, volunteer)."""
    normalized_allowed = [r.lower().replace(" ", "").replace("_", "") for r in allowed_roles]

    async def role_checker(
        current_user: User = Depends(get_current_user)
    ) -> User:
        if getattr(current_user, "is_superuser", False):
            return current_user

        user_role_str = getattr(current_user, "role", "") or ""
        # If user has roles relationship
        user_roles_list = [user_role_str]
        if hasattr(current_user, "roles") and current_user.roles:
            for ur in current_user.roles:
                if hasattr(ur, "role") and hasattr(ur.role, "code"):
                    user_roles_list.append(ur.role.code)

        for r in user_roles_list:
            norm_r = r.lower().replace(" ", "").replace("_", "")
            if norm_r == "superadmin":
                return current_user
            if norm_r in normalized_allowed:
                return current_user

        raise PermissionDeniedException(
            permission=",".join(allowed_roles),
            message=f"Access denied. Requires one of roles: {', '.join(allowed_roles)}."
        )

    return role_checker


def require_permissions(*required_permissions: str) -> Callable:
    """Dependency factory checking that current user possesses required permissions."""
    async def permission_checker(
        current_user: User = Depends(get_current_user)
    ) -> User:
        if getattr(current_user, "is_superuser", False):
            return current_user

        user_permissions: set[str] = set()
        if hasattr(current_user, "roles") and current_user.roles:
            for user_role in current_user.roles:
                if hasattr(user_role, "role") and hasattr(user_role.role, "permissions"):
                    for rp in user_role.role.permissions:
                        if hasattr(rp, "permission") and hasattr(rp.permission, "code"):
                            user_permissions.add(rp.permission.code)

        for perm in required_permissions:
            if perm not in user_permissions:
                # Also allow superadmin/admin fallback for standard operations
                role_val = (getattr(current_user, "role", "") or "").lower()
                if "superadmin" in role_val or "admin" in role_val:
                    continue
                raise PermissionDeniedException(
                    permission=perm,
                    message=f"Access denied. Required permission '{perm}' is missing."
                )
        return current_user

    return permission_checker


async def require_super_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """Enforces that the user is a platform SUPER_ADMIN."""
    if getattr(current_user, "is_superuser", False):
        return current_user

    role_val = (getattr(current_user, "role", "") or "").lower()
    if "superadmin" in role_val:
        return current_user

    if hasattr(current_user, "roles") and current_user.roles:
        for user_role in current_user.roles:
            if hasattr(user_role, "role") and hasattr(user_role.role, "code"):
                if user_role.role.code in [RoleCode.SUPER_ADMIN.value, "SUPER_ADMIN", "superadmin"]:
                    return current_user

    raise PermissionDeniedException(
        permission=PermissionCode.SYSTEM_MANAGE.value,
        message="Super Admin privileges are required to perform this platform operation."
    )


async def get_current_org_id(
    current_user: User = Depends(get_current_user),
    x_organization_id: Optional[str] = Header(None, alias="X-Organization-ID")
) -> str:
    """Extracts tenant organization ID."""
    if getattr(current_user, "is_superuser", False) and x_organization_id:
        return x_organization_id
    return getattr(current_user, "organization_id", None) or "default_org"


def get_tenant_scope(
    allow_cross_tenant_if_superuser: bool = True
) -> Callable:
    """Resolves and validates the organization scope for multi-tenant isolation."""
    async def tenant_resolver(
        request: Request,
        current_user: User = Depends(get_current_user),
        x_organization_id: Optional[str] = Header(None, alias="X-Organization-ID")
    ) -> Optional[str]:
        if getattr(current_user, "is_superuser", False):
            return x_organization_id or getattr(current_user, "organization_id", None)

        user_org_id = getattr(current_user, "organization_id", None)
        if not user_org_id:
            raise PermissionDeniedException(message="User is not associated with any organization.")

        if x_organization_id and x_organization_id != user_org_id:
            raise PermissionDeniedException(
                message="Cross-tenant access violation: You cannot access resources belonging to another organization."
            )

        return user_org_id

    return tenant_resolver
