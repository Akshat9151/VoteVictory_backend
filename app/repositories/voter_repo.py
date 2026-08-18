from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.voter import Voter, VoterCheckin
from app.repositories.base import BaseRepository


class VoterRepository(BaseRepository[Voter]):
    def __init__(self, db: AsyncSession):
        super().__init__(Voter, db)

    async def get_by_voter_id_number(self, election_id: str, voter_id_number: str) -> Optional[Voter]:
        stmt = (
            select(Voter)
            .where(
                Voter.election_id == election_id,
                Voter.voter_id_number == voter_id_number.strip().upper()
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_checkin(self, election_id: str, voter_id: str) -> Optional[VoterCheckin]:
        stmt = (
            select(VoterCheckin)
            .where(
                VoterCheckin.election_id == election_id,
                VoterCheckin.voter_id == voter_id
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()
