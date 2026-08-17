from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permissions
from app.core.permissions import PermissionCode
from app.models.user import User
from app.schemas.common import APIResponse, PaginatedResponse
from app.schemas.role import PermissionResponse, RoleResponse
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["User Management"])


def serialize_user(user: User) -> UserResponse:
    roles = [ur.role.code for ur in user.roles if ur.role]
    permissions = set()
    for ur in user.roles:
        if ur.role:
            for rp in ur.role.permissions:
                if rp.permission:
                    permissions.add(rp.permission.code)

    return UserResponse(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        phone=user.phone,
        organization_id=user.organization_id,
        is_active=user.is_active,
        is_verified=user.is_verified,
        is_superuser=user.is_superuser,
        mfa_enabled=user.mfa_enabled,
        last_login_at=user.last_login_at,
        roles=roles,
        permissions=list(permissions),
        created_at=user.created_at
    )


@router.get("/me", response_model=APIResponse[UserResponse])
async def get_my_profile(current_user: User = Depends(get_current_user)):
    return APIResponse(data=serialize_user(current_user))


@router.get("/", response_model=APIResponse[PaginatedResponse[UserResponse]])
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    org_id: Optional[str] = None,
    current_user: User = Depends(require_permissions(PermissionCode.USER_VIEW.value)),
    db: AsyncSession = Depends(get_db)
):
    service = UserService(db)
    users, pagination = await service.list_users(
        current_user=current_user,
        org_id=org_id,
        page=page,
        page_size=page_size,
        search=search
    )
    items = [serialize_user(u) for u in users]
    return APIResponse(data=PaginatedResponse(items=items, pagination=pagination))


@router.post("/", response_model=APIResponse[UserResponse])
async def create_user(
    request: Request,
    user_in: UserCreate,
    current_user: User = Depends(require_permissions(PermissionCode.USER_CREATE.value)),
    db: AsyncSession = Depends(get_db)
):
    service = UserService(db)
    user = await service.create_user(request, user_in, current_user)
    return APIResponse(
        success=True,
        message="User successfully created.",
        data=serialize_user(user)
    )


@router.get("/roles/all", response_model=APIResponse[List[RoleResponse]])
async def list_roles(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = UserService(db)
    roles = await service.get_roles()
    role_items = [
        RoleResponse(
            id=r.id,
            organization_id=r.organization_id,
            name=r.name,
            code=r.code,
            is_system=r.is_system,
            description=r.description,
            permissions=[rp.permission.code for rp in r.permissions if rp.permission],
            created_at=r.created_at
        )
        for r in roles
    ]
    return APIResponse(data=role_items)


@router.get("/permissions/all", response_model=APIResponse[List[PermissionResponse]])
async def list_permissions(
    current_user: User = Depends(require_permissions(PermissionCode.PERMISSION_MANAGE.value)),
    db: AsyncSession = Depends(get_db)
):
    service = UserService(db)
    perms = await service.get_permissions()
    items = [PermissionResponse.model_validate(p) for p in perms]
    return APIResponse(data=items)


@router.get("/{user_id}", response_model=APIResponse[UserResponse])
async def get_user_by_id(
    user_id: str,
    current_user: User = Depends(require_permissions(PermissionCode.USER_VIEW.value)),
    db: AsyncSession = Depends(get_db)
):
    service = UserService(db)
    user = await service.get_user(user_id, current_user)
    return APIResponse(data=serialize_user(user))


@router.put("/{user_id}", response_model=APIResponse[UserResponse])
async def update_user(
    request: Request,
    user_id: str,
    user_in: UserUpdate,
    current_user: User = Depends(require_permissions(PermissionCode.USER_UPDATE.value)),
    db: AsyncSession = Depends(get_db)
):
    service = UserService(db)
    user = await service.update_user(request, user_id, user_in, current_user)
    return APIResponse(
        success=True,
        message="User profile updated.",
        data=serialize_user(user)
    )
