from sqlalchemy.ext.asyncio import AsyncSession

from app.models.broadcast import DeliveryLog
from app.repositories.base import BaseRepository


class DeliveryLogRepository(BaseRepository[DeliveryLog]):
    def __init__(self, db: AsyncSession):
        super().__init__(DeliveryLog, db)

    async def create_batch(self, logs: list[DeliveryLog]) -> list[DeliveryLog]:
        if not logs:
            return []
        self.db.add_all(logs)
        await self.db.flush()
        for log in logs:
            await self.db.refresh(log)
        return logs
