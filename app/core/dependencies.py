from typing import Callable, List, Optional
from fastapi import Depends, Header, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.exceptions import AuthenticationException, PermissionDeniedException
from app.core.permissions import PermissionCode, RoleCode
from app.core.rate_limit import rate_limiter
from app.core.security import decode_access_token
from app.models.user import User
from app.repositories.user_repo import UserRepository

security_scheme = HTTPBearer(auto_error=False)


async def check_rate_limit(request: Request) -> None:
    """Rate limit dependency checking client IP."""
    await rate_limiter.check_rate_limit(request)


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
    user = await user_repo.get_with_roles(user_id)
    if not user:
        raise AuthenticationException("User account associated with token no longer exists.")

    if not user.is_active:
        raise AuthenticationException("User account is deactivated.")

    # Cache user on request state for audit logs
    request.state.current_user = user
    return user


def require_permissions(*required_permissions: str) -> Callable:
    """Dependency factory checking that current user possesses required permissions."""
    async def permission_checker(
        current_user: User = Depends(get_current_user)
    ) -> User:
        if current_user.is_superuser:
            return current_user

        user_permissions: set[str] = set()
        for user_role in current_user.roles:
            role = user_role.role
            for rp in role.permissions:
                user_permissions.add(rp.permission.code)

        for perm in required_permissions:
            if perm not in user_permissions:
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
    if current_user.is_superuser:
        return current_user

    for user_role in current_user.roles:
        if user_role.role.code == RoleCode.SUPER_ADMIN.value:
            return current_user

    raise PermissionDeniedException(
        permission=PermissionCode.SYSTEM_MANAGE.value,
        message="Super Admin privileges are required to perform this platform operation."
    )


def get_tenant_scope(
    allow_cross_tenant_if_superuser: bool = True
) -> Callable:
    """Resolves and validates the organization scope for multi-tenant isolation."""
    async def tenant_resolver(
        request: Request,
        current_user: User = Depends(get_current_user),
        x_organization_id: Optional[str] = Header(None, alias="X-Organization-ID")
    ) -> Optional[str]:
        # If user is Super Admin, they can operate on behalf of any org passed in header/query
        if current_user.is_superuser:
            return x_organization_id or current_user.organization_id

        user_org_id = current_user.organization_id
        if not user_org_id:
            raise PermissionDeniedException(message="User is not associated with any organization.")

        if x_organization_id and x_organization_id != user_org_id:
            raise PermissionDeniedException(
                message="Cross-tenant access violation: You cannot access resources belonging to another organization."
            )

        return user_org_id

    return tenant_resolver
