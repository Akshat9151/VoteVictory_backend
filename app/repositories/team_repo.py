from sqlalchemy.ext.asyncio import AsyncSession

from app.models.team import TeamMember, Volunteer
from app.repositories.base import BaseRepository


class TeamMemberRepository(BaseRepository[TeamMember]):
    def __init__(self, db: AsyncSession):
        super().__init__(TeamMember, db)


class VolunteerRepository(BaseRepository[Volunteer]):
    def __init__(self, db: AsyncSession):
        super().__init__(Volunteer, db)
