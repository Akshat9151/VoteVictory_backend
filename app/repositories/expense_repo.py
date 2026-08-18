from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.expense import Expense
from app.repositories.base import BaseRepository


class ExpenseRepository(BaseRepository[Expense]):
    def __init__(self, db: AsyncSession):
        super().__init__(Expense, db)

    async def get_total_spent(self, organization_id: Optional[str] = None) -> float:
        stmt = select(func.coalesce(func.sum(Expense.amount), 0.0))
        if organization_id:
            stmt = stmt.where(Expense.organization_id == organization_id)
        result = await self.db.execute(stmt)
        return float(result.scalar() or 0.0)
