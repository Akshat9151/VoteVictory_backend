from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.volunteer_voter import VolunteerVoter
from app.repositories.base import BaseRepository


class VolunteerVoterRepository(BaseRepository[VolunteerVoter]):
    def __init__(self, db: AsyncSession):
        super().__init__(VolunteerVoter, db)
