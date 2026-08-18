from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import Permission, Role, RolePermission, User, UserRole, UserSession
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, db: AsyncSession):
        super().__init__(User, db)

    async def get_by_email(self, email: str) -> Optional[User]:
        stmt = (
            select(User)
            .options(
                selectinload(User.roles).selectinload(UserRole.role).selectinload(Role.permissions).selectinload(RolePermission.permission)
            )
            .where(User.email == email.lower().strip())
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_by_phone(self, phone: str) -> Optional[User]:
        cleaned = phone.strip()
        stmt = (
            select(User)
            .options(
                selectinload(User.roles).selectinload(UserRole.role).selectinload(Role.permissions).selectinload(RolePermission.permission)
            )
            .where((User.phone == cleaned) | (User.phone.contains(cleaned.replace(" ", ""))))
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_first_user(self) -> Optional[User]:
        stmt = (
            select(User)
            .options(
                selectinload(User.roles).selectinload(UserRole.role).selectinload(Role.permissions).selectinload(RolePermission.permission)
            )
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_with_roles(self, user_id: str) -> Optional[User]:
        stmt = (
            select(User)
            .options(
                selectinload(User.roles).selectinload(UserRole.role).selectinload(Role.permissions).selectinload(RolePermission.permission)
            )
            .where(User.id == user_id)
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_role_by_code(self, code: str) -> Optional[Role]:
        stmt = (
            select(Role)
            .options(selectinload(Role.permissions).selectinload(RolePermission.permission))
            .where(Role.code == code)
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_all_roles(self) -> List[Role]:
        stmt = select(Role).options(selectinload(Role.permissions).selectinload(RolePermission.permission))
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_all_permissions(self) -> List[Permission]:
        stmt = select(Permission)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_session(self, session: UserSession) -> UserSession:
        self.db.add(session)
        await self.db.flush()
        return session

    async def get_session_by_hash(self, token_hash: str) -> Optional[UserSession]:
        stmt = select(UserSession).where(UserSession.refresh_token_hash == token_hash)
        result = await self.db.execute(stmt)
        return result.scalars().first()
