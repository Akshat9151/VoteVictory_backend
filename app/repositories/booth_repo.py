from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booth import Booth
from app.repositories.base import BaseRepository


class BoothRepository(BaseRepository[Booth]):
    def __init__(self, db: AsyncSession):
        super().__init__(Booth, db)
