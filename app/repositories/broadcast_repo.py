from sqlalchemy.ext.asyncio import AsyncSession
from app.models.broadcast import DeliveryLog
from app.repositories.base import BaseRepository


class DeliveryLogRepository(BaseRepository[DeliveryLog]):
    def __init__(self, db: AsyncSession):
        super().__init__(DeliveryLog, db)
