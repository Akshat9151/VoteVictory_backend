from typing import Any, Dict, List, Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.voting import Ballot, Vote, VotingSession, VotingSessionStatus
from app.repositories.base import BaseRepository


class VotingRepository(BaseRepository[Ballot]):
    def __init__(self, db: AsyncSession):
        super().__init__(Ballot, db)

    async def get_session_by_hash(self, token_hash: str) -> Optional[VotingSession]:
        stmt = select(VotingSession).where(
            VotingSession.voter_token_hash == token_hash,
            VotingSession.status == VotingSessionStatus.ACTIVE
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def create_session(self, session: VotingSession) -> VotingSession:
        self.db.add(session)
        await self.db.flush()
        return session

    async def record_anonymous_ballot(self, ballot: Ballot, votes: List[Vote]) -> Ballot:
        self.db.add(ballot)
        await self.db.flush()
        for vote in votes:
            vote.ballot_id = ballot.id
            self.db.add(vote)
        await self.db.flush()
        return ballot

    async def get_vote_counts_by_candidate(self, election_id: str) -> List[Dict[str, Any]]:
        stmt = (
            select(
                Vote.position_id,
                Vote.candidate_id,
                func.count(Vote.id).label("vote_count")
            )
            .join(Ballot, Ballot.id == Vote.ballot_id)
            .where(Ballot.election_id == election_id, Ballot.is_valid == True)
            .group_by(Vote.position_id, Vote.candidate_id)
        )
        result = await self.db.execute(stmt)
        rows = result.all()
        return [
            {"position_id": row[0], "candidate_id": row[1], "vote_count": row[2]}
            for row in rows
        ]

    async def get_total_ballots_cast(self, election_id: str) -> int:
        stmt = (
            select(func.count(Ballot.id))
            .where(Ballot.election_id == election_id, Ballot.is_valid == True)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one() or 0
