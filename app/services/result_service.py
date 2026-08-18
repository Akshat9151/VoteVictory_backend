from datetime import datetime, timezone

from fastapi import Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit_log
from app.core.exceptions import AppException, ResourceNotFoundException
from app.models.candidate import Candidate
from app.models.election import ElectionStatus, Position
from app.models.result import Result, ResultStatus, ResultSummary
from app.models.user import User
from app.models.voter import Voter, VoterCheckin
from app.models.voting import Ballot, Vote
from app.repositories.election_repo import ElectionRepository
from app.repositories.voting_repo import VotingRepository
from app.schemas.result import (
    CandidateResultItem,
    ElectionResultSummaryResponse,
    PositionResultResponse,
    ResultPublishRequest,
)


class ResultService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.voting_repo = VotingRepository(db)
        self.election_repo = ElectionRepository(db)

    async def tally_results(self, request: Request, election_id: str, current_user: User) -> ElectionResultSummaryResponse:
        election = await self.election_repo.get_by_id(election_id)
        if not election:
            raise ResourceNotFoundException("Election", election_id)

        # 1. Total statistics
        total_eligible = (await self.db.execute(
            select(func.count(Voter.id)).where(Voter.election_id == election_id)
        )).scalar_one() or 0

        total_checked_in = (await self.db.execute(
            select(func.count(VoterCheckin.id)).where(VoterCheckin.election_id == election_id)
        )).scalar_one() or 0

        total_ballots = await self.voting_repo.get_total_ballots_cast(election_id)
        turnout = (total_ballots / total_eligible * 100) if total_eligible > 0 else 0.0

        # 2. Clear old draft tallies
        await self.db.execute(
            Result.__table__.delete().where(Result.election_id == election_id)
        )

        # 3. Tally votes per position
        positions_res = await self.db.execute(
            select(Position).where(Position.election_id == election_id).order_by(Position.display_order.asc())
        )
        positions = positions_res.scalars().all()

        now = datetime.now(timezone.utc)
        position_results = []

        for pos in positions:
            # Query candidate counts for this position
            candidates_res = await self.db.execute(
                select(Candidate).where(Candidate.position_id == pos.id)
            )
            candidates = candidates_res.scalars().all()

            pos_votes_stmt = (
                select(Vote.candidate_id, func.count(Vote.id))
                .join(Ballot, Ballot.id == Vote.ballot_id)
                .where(Ballot.election_id == election_id, Vote.position_id == pos.id, Ballot.is_valid == True)
                .group_by(Vote.candidate_id)
            )
            count_map = dict((await self.db.execute(pos_votes_stmt)).all())

            total_pos_votes = sum(count_map.values())
            candidate_items = []

            for cand in candidates:
                votes_for_cand = count_map.get(cand.id, 0)
                pct = (votes_for_cand / total_pos_votes * 100) if total_pos_votes > 0 else 0.0
                candidate_items.append({
                    "candidate_id": cand.id,
                    "candidate_name": cand.full_name,
                    "party_name": cand.party_name,
                    "vote_count": votes_for_cand,
                    "vote_percentage": round(pct, 2)
                })

            # Sort by vote count descending to calculate rank
            candidate_items.sort(key=lambda x: x["vote_count"], reverse=True)
            for rank, item in enumerate(candidate_items, start=1):
                item["rank"] = rank
                # Persist result row
                result_row = Result(
                    election_id=election_id,
                    position_id=pos.id,
                    candidate_id=item["candidate_id"],
                    vote_count=item["vote_count"],
                    vote_percentage=item["vote_percentage"],
                    rank=rank,
                    status=ResultStatus.COUNTING,
                    counted_at=now
                )
                self.db.add(result_row)

            position_results.append(
                PositionResultResponse(
                    position_id=pos.id,
                    position_title=pos.title,
                    total_votes=total_pos_votes,
                    candidates=[CandidateResultItem(**c) for c in candidate_items]
                )
            )

        # 4. Update or create ResultSummary
        summary_res = await self.db.execute(
            select(ResultSummary).where(ResultSummary.election_id == election_id)
        )
        summary = summary_res.scalars().first()
        if not summary:
            summary = ResultSummary(
                election_id=election_id,
                total_eligible_voters=total_eligible,
                total_checked_in=total_checked_in,
                total_votes_cast=total_ballots,
                turnout_percentage=round(turnout, 2),
                status=ResultStatus.UNDER_REVIEW
            )
            self.db.add(summary)
        else:
            summary.total_eligible_voters = total_eligible
            summary.total_checked_in = total_checked_in
            summary.total_votes_cast = total_ballots
            summary.turnout_percentage = round(turnout, 2)
            summary.status = ResultStatus.UNDER_REVIEW

        await self.db.flush()

        await record_audit_log(
            self.db,
            request,
            action="result.tally",
            resource_type="result_summary",
            resource_id=summary.id,
            organization_id=election.organization_id,
            current_user=current_user,
            new_state={"total_votes_cast": total_ballots, "turnout": round(turnout, 2)}
        )

        return ElectionResultSummaryResponse(
            election_id=election.id,
            election_title=election.title,
            status=summary.status,
            total_eligible_voters=total_eligible,
            total_checked_in=total_checked_in,
            total_votes_cast=total_ballots,
            turnout_percentage=round(turnout, 2),
            results_by_position=position_results,
            counted_at=now
        )

    async def publish_results(self, request: Request, pub_in: ResultPublishRequest, current_user: User) -> ElectionResultSummaryResponse:
        election_id = pub_in.election_id
        summary_res = await self.db.execute(
            select(ResultSummary).where(ResultSummary.election_id == election_id)
        )
        summary = summary_res.scalars().first()
        if not summary:
            raise AppException(code="RESULTS_NOT_COUNTED", message="Results must be tallied before publication.")

        now = datetime.now(timezone.utc)
        summary.status = ResultStatus.PUBLISHED
        summary.approved_by = current_user.id
        summary.approved_at = now
        summary.published_at = now
        summary.notes = pub_in.notes
        self.db.add(summary)

        # Update election status
        election = await self.election_repo.get_by_id(election_id)
        if election:
            election.status = ElectionStatus.RESULT_PUBLISHED
            await self.election_repo.update(election)

        # Update individual result rows
        await self.db.execute(
            Result.__table__.update().where(Result.election_id == election_id).values(
                status=ResultStatus.PUBLISHED,
                published_at=now,
                approved_by=current_user.id
            )
        )

        await record_audit_log(
            self.db,
            request,
            action="result.publish",
            resource_type="result_summary",
            resource_id=summary.id,
            organization_id=election.organization_id if election else None,
            current_user=current_user,
            new_state={"status": ResultStatus.PUBLISHED.value, "published_at": now.isoformat()}
        )

        return await self.get_results(election_id)

    async def get_results(self, election_id: str) -> ElectionResultSummaryResponse:
        election = await self.election_repo.get_by_id(election_id)
        if not election:
            raise ResourceNotFoundException("Election", election_id)

        summary_res = await self.db.execute(
            select(ResultSummary).where(ResultSummary.election_id == election_id)
        )
        summary = summary_res.scalars().first()
        status_val = summary.status if summary else ResultStatus.NOT_STARTED

        # Positions & Candidates
        positions_res = await self.db.execute(
            select(Position).where(Position.election_id == election_id).order_by(Position.display_order.asc())
        )
        positions = positions_res.scalars().all()

        pos_results = []
        for pos in positions:
            res_stmt = (
                select(Result, Candidate)
                .join(Candidate, Candidate.id == Result.candidate_id)
                .where(Result.position_id == pos.id)
                .order_by(Result.rank.asc())
            )
            rows = (await self.db.execute(res_stmt)).all()
            candidate_items = [
                CandidateResultItem(
                    candidate_id=cand.id,
                    candidate_name=cand.full_name,
                    party_name=cand.party_name,
                    vote_count=res.vote_count,
                    vote_percentage=res.vote_percentage,
                    rank=res.rank
                )
                for res, cand in rows
            ]
            total_votes = sum(c.vote_count for c in candidate_items)
            pos_results.append(
                PositionResultResponse(
                    position_id=pos.id,
                    position_title=pos.title,
                    total_votes=total_votes,
                    candidates=candidate_items
                )
            )

        return ElectionResultSummaryResponse(
            election_id=election.id,
            election_title=election.title,
            status=status_val,
            total_eligible_voters=summary.total_eligible_voters if summary else 0,
            total_checked_in=summary.total_checked_in if summary else 0,
            total_votes_cast=summary.total_votes_cast if summary else 0,
            turnout_percentage=summary.turnout_percentage if summary else 0.0,
            results_by_position=pos_results,
            counted_at=summary.created_at if summary else None,
            approved_by=summary.approved_by if summary else None,
            published_at=summary.published_at if summary else None
        )
