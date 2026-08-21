from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.complaint import Complaint
from app.repositories.base import BaseRepository


class ComplaintRepository(BaseRepository[Complaint]):
    def __init__(self, db: AsyncSession):
        super().__init__(Complaint, db)

    async def get_by_id(self, id: str, organization_id: str | None = None):
        statement = select(Complaint).options(selectinload(Complaint.created_by)).where(Complaint.id == id)
        if organization_id:
            statement = statement.where(Complaint.organization_id == organization_id)
        result = await self.db.execute(statement)
        return result.scalars().first()

    async def list_all(self, filters=None, organization_id=None, limit=None, order_by=None):
        statement = select(Complaint).options(selectinload(Complaint.created_by))
        if organization_id:
            statement = statement.where(Complaint.organization_id == organization_id)
        for field, value in (filters or {}).items():
            if value is not None:
                statement = statement.where(getattr(Complaint, field) == value)
        if order_by is not None:
            statement = statement.order_by(order_by)
        if limit is not None:
            statement = statement.limit(limit)
        result = await self.db.execute(statement)
        return list(result.scalars().all())
