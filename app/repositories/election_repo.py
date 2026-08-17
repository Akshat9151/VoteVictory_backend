from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.election import Constituency, Election, ElectionSetting, Position
from app.repositories.base import BaseRepository


class ElectionRepository(BaseRepository[Election]):
    def __init__(self, db: AsyncSession):
        super().__init__(Election, db)

    async def get_by_id_loaded(self, election_id: str) -> Optional[Election]:
        stmt = (
            select(Election)
            .options(
                selectinload(Election.settings),
                selectinload(Election.positions),
                selectinload(Election.constituencies),
            )
            .where(Election.id == election_id)
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_by_slug(self, org_id: str, slug: str) -> Optional[Election]:
        stmt = (
            select(Election)
            .options(selectinload(Election.settings))
            .where(Election.organization_id == org_id, Election.slug == slug)
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def list_by_organization(self, org_id: str) -> List[Election]:
        stmt = select(Election).options(selectinload(Election.settings)).where(Election.organization_id == org_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
