from sqlalchemy.ext.asyncio import AsyncSession

from app.models.complaint import Complaint
from app.repositories.base import BaseRepository


class ComplaintRepository(BaseRepository[Complaint]):
    def __init__(self, db: AsyncSession):
        super().__init__(Complaint, db)
