from typing import List, Optional, Tuple

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit_log
from app.core.exceptions import DuplicateResourceException, PermissionDeniedException, ResourceNotFoundException
from app.core.permissions import RoleCode
from app.core.security import get_password_hash
from app.models.user import Permission, Role, User, UserRole
from app.repositories.user_repo import UserRepository
from app.schemas.common import PaginationMeta
from app.schemas.user import UserCreate, UserUpdate


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)

    async def create_user(
        self,
        request: Request,
        user_in: UserCreate,
        current_user: User,
        target_org_id: Optional[str] = None
    ) -> User:
        # Check duplicate email
        existing = await self.user_repo.get_by_email(user_in.email)
        if existing:
            raise DuplicateResourceException("User", "email", user_in.email)

        # Enforce Org Scope: Non-superusers can only create users in their own org
        org_id = target_org_id or user_in.organization_id or current_user.organization_id
        if not current_user.is_superuser:
            org_id = current_user.organization_id
            if user_in.role_code == RoleCode.SUPER_ADMIN.value:
                raise PermissionDeniedException(message="Only Super Admin can assign the SUPER_ADMIN role.")

        user = User(
            email=user_in.email.lower().strip(),
            first_name=user_in.first_name.strip(),
            last_name=user_in.last_name.strip(),
            phone=user_in.phone,
            organization_id=org_id,
            password_hash=get_password_hash(user_in.password),
            is_active=user_in.is_active,
            is_verified=True,
            is_superuser=(user_in.role_code == RoleCode.SUPER_ADMIN.value and current_user.is_superuser)
        )
        user = await self.user_repo.create(user)

        # Bind Role
        role = await self.user_repo.get_role_by_code(user_in.role_code)
        if role:
            user_role = UserRole(user_id=user.id, role_id=role.id)
            self.db.add(user_role)
            await self.db.flush()

        await record_audit_log(
            self.db,
            request,
            action="user.create",
            resource_type="user",
            resource_id=user.id,
            current_user=current_user,
            new_state={"email": user.email, "role": user_in.role_code, "org_id": org_id}
        )

        return await self.user_repo.get_with_roles(user.id)

    async def list_users(
        self,
        current_user: User,
        org_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None
    ) -> Tuple[List[User], PaginationMeta]:
        filters = {}
        if not current_user.is_superuser:
            filters["organization_id"] = current_user.organization_id
        elif org_id:
            filters["organization_id"] = org_id

        return await self.user_repo.list_paginated(
            page=page,
            page_size=page_size,
            filters=filters,
            search_query=search,
            search_fields=["first_name", "last_name", "email", "phone"]
        )

    async def get_user(self, user_id: str, current_user: User) -> User:
        user = await self.user_repo.get_with_roles(user_id)
        if not user:
            raise ResourceNotFoundException("User", user_id)

        if not current_user.is_superuser and user.organization_id != current_user.organization_id:
            raise PermissionDeniedException(message="Access to cross-tenant user denied.")

        return user

    async def update_user(
        self,
        request: Request,
        user_id: str,
        user_in: UserUpdate,
        current_user: User
    ) -> User:
        user = await self.get_user(user_id, current_user)
        prev_state = {"first_name": user.first_name, "last_name": user.last_name, "is_active": user.is_active}

        if user_in.first_name is not None:
            user.first_name = user_in.first_name.strip()
        if user_in.last_name is not None:
            user.last_name = user_in.last_name.strip()
        if user_in.phone is not None:
            user.phone = user_in.phone
        if user_in.is_active is not None:
            user.is_active = user_in.is_active

        updated = await self.user_repo.update(user)

        await record_audit_log(
            self.db,
            request,
            action="user.update",
            resource_type="user",
            resource_id=user.id,
            current_user=current_user,
            prev_state=prev_state,
            new_state={"first_name": user.first_name, "last_name": user.last_name, "is_active": user.is_active}
        )
        return updated

    async def delete_user(self, request: Optional[Request], user_id: str, current_user: User) -> bool:
        user = await self.get_user(user_id, current_user)
        user.is_active = False
        await self.user_repo.update(user)
        await record_audit_log(
            self.db,
            request,
            action="user.deactivate",
            resource_type="user",
            resource_id=user.id,
            current_user=current_user,
            details={"message": f"Deactivated user {user.email}"},
        )
        return True

    async def get_roles(self) -> List[Role]:
        return await self.user_repo.get_all_roles()

    async def get_permissions(self) -> List[Permission]:
        return await self.user_repo.get_all_permissions()

