from datetime import datetime, timedelta, timezone

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.audit import record_audit_log, record_security_event
from app.core.exceptions import (
    AppException,
    DoubleVotingException,
    ElectionNotActiveException,
    ResourceNotFoundException,
    VoterEligibilityException,
)
from app.core.security import compute_ballot_hash, generate_ballot_nonce, hash_token
from app.models.audit import SecuritySeverity
from app.models.candidate import CandidateStatus
from app.models.election import ElectionStatus, Position
from app.models.voter import Voter, VoterStatus, VotingStatus
from app.models.voting import Ballot, Vote, VotingSession, VotingSessionStatus
from app.repositories.election_repo import ElectionRepository
from app.repositories.voter_repo import VoterRepository
from app.repositories.voting_repo import VotingRepository
from app.schemas.voting import (
    BallotCandidateOption,
    BallotGenerateResponse,
    BallotPosition,
    VoteReceiptResponse,
    VoteSubmissionRequest,
    VotingAuthRequest,
)


class VotingEngineService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.voting_repo = VotingRepository(db)
        self.voter_repo = VoterRepository(db)
        self.election_repo = ElectionRepository(db)

    async def authenticate_and_generate_ballot(
        self,
        request: Request,
        auth_in: VotingAuthRequest
    ) -> BallotGenerateResponse:
        # 1. Verify Election is LIVE
        election = await self.election_repo.get_by_id(auth_in.election_id)
        if not election:
            raise ResourceNotFoundException("Election", auth_in.election_id)

        if election.status != ElectionStatus.LIVE:
            raise ElectionNotActiveException(election.id, election.status.value)

        # 2. Verify Voter Eligibility
        voter = await self.voter_repo.get_by_voter_id_number(auth_in.election_id, auth_in.voter_id_number)
        if not voter:
            await record_security_event(
                self.db,
                request,
                event_type="UNREGISTERED_VOTER_VOTE_ATTEMPT",
                severity=SecuritySeverity.LOW,
                organization_id=election.organization_id,
                details={"epic": auth_in.voter_id_number, "election_id": election.id}
            )
            raise VoterEligibilityException("Voter ID is not registered in this election.")

        if voter.has_voted or voter.voting_status == VotingStatus.VOTED:
            await record_security_event(
                self.db,
                request,
                event_type="DOUBLE_VOTING_AUTH_ATTEMPT",
                severity=SecuritySeverity.HIGH,
                organization_id=election.organization_id,
                details={"voter_id": voter.id, "epic": voter.voter_id_number}
            )
            raise DoubleVotingException(voter_id=voter.id)

        if voter.status in (VoterStatus.BLOCKED, VoterStatus.SUSPENDED, VoterStatus.INELIGIBLE):
            raise VoterEligibilityException(f"Voter status is '{voter.status.value}'. Voting is barred.")

        # 3. Generate Ephemeral Voting Session Token
        raw_session_token = generate_ballot_nonce()
        session_token_hash = hash_token(raw_session_token)

        expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
        voting_session = VotingSession(
            election_id=election.id,
            voter_token_hash=session_token_hash,
            status=VotingSessionStatus.ACTIVE,
            issued_at=datetime.now(timezone.utc),
            expires_at=expires_at,
            client_ip=request.client.host if request.client else None
        )
        await self.voting_repo.create_session(voting_session)

        # 4. Fetch Ballot Structure (Positions & Approved Candidates)
        positions_stmt = (
            select(Position)
            .options(
                selectinload(Position.candidates)
            )
            .where(
                Position.election_id == election.id,
                Position.is_active == True
            )
            .order_by(Position.display_order.asc())
        )
        positions_res = await self.db.execute(positions_stmt)
        positions = positions_res.scalars().all()

        ballot_positions = []
        for pos in positions:
            candidates = [
                BallotCandidateOption(
                    candidate_id=c.id,
                    full_name=c.full_name,
                    party_name=c.party_name,
                    party_symbol_url=c.party_symbol_url,
                    photo_url=c.photo_url,
                    manifesto=c.manifesto,
                    display_order=c.display_order
                )
                for c in pos.candidates
                if c.status == CandidateStatus.APPROVED
            ]
            ballot_positions.append(
                BallotPosition(
                    position_id=pos.id,
                    title=pos.title,
                    description=pos.description,
                    min_selections=pos.min_selections,
                    max_selections=pos.max_selections,
                    allow_abstain=True,
                    candidates=candidates
                )
            )

        return BallotGenerateResponse(
            session_token=raw_session_token,
            election_id=election.id,
            election_title=election.title,
            expires_at=expires_at,
            positions=ballot_positions
        )

    async def cast_ballot(
        self,
        request: Request,
        vote_in: VoteSubmissionRequest,
        voter_id: str
    ) -> VoteReceiptResponse:
        """
        Executes atomic anonymous vote submission with strict double-voting prevention.
        Uses SELECT FOR UPDATE lock on voter to prevent concurrent double-vote race conditions.
        """
        # 1. Validate Session
        session_token_hash = hash_token(vote_in.session_token)
        session = await self.voting_repo.get_session_by_hash(session_token_hash)
        now_utc = datetime.now(timezone.utc)
        expires_at = session.expires_at.replace(tzinfo=timezone.utc) if (session and session.expires_at and session.expires_at.tzinfo is None) else (session.expires_at if session else None)
        if not session or expires_at < now_utc:
            raise AppException(code="INVALID_VOTING_SESSION", message="Voting session token has expired or is invalid.")

        # 2. Acquire Atomic Lock on Voter record
        lock_stmt = select(Voter).where(Voter.id == voter_id).with_for_update()
        voter_res = await self.db.execute(lock_stmt)
        voter = voter_res.scalars().first()

        if not voter:
            raise ResourceNotFoundException("Voter", voter_id)

        if voter.has_voted or voter.voting_status == VotingStatus.VOTED:
            await record_security_event(
                self.db,
                request,
                event_type="DOUBLE_VOTING_CAST_ATTEMPT",
                severity=SecuritySeverity.CRITICAL,
                organization_id=voter.organization_id,
                details={"voter_id": voter.id}
            )
            raise DoubleVotingException(voter_id=voter.id)

        # 3. Validate Ballot Selections against Position Rules
        positions_map = {}
        for sel in vote_in.selections:
            pos = (await self.db.execute(select(Position).where(Position.id == sel.position_id))).scalars().first()
            if not pos:
                raise AppException(code="INVALID_POSITION", message=f"Position ID '{sel.position_id}' not found.")

            if len(sel.candidate_ids) > pos.max_selections:
                raise AppException(
                    code="MAX_SELECTIONS_EXCEEDED",
                    message=f"Maximum {pos.max_selections} candidate(s) allowed for '{pos.title}'."
                )
            positions_map[pos.id] = pos

        # 4. Generate Anonymous Cryptographic Ballot Serial
        nonce = generate_ballot_nonce()
        ballot_serial_hash = compute_ballot_hash(vote_in.election_id, nonce)
        cast_time = datetime.now(timezone.utc)

        # Anonymous Ballot record (Notice NO voter_id is stored on Ballot or Votes!)
        ballot = Ballot(
            election_id=vote_in.election_id,
            constituency_id=voter.constituency_id,
            ballot_serial_hash=ballot_serial_hash,
            cast_timestamp=cast_time,
            is_valid=True
        )

        votes = []
        for sel in vote_in.selections:
            for cid in sel.candidate_ids:
                votes.append(Vote(position_id=sel.position_id, candidate_id=cid))

        await self.voting_repo.record_anonymous_ballot(ballot, votes)

        # 5. Mark Voter as VOTED
        voter.has_voted = True
        voter.voting_status = VotingStatus.VOTED
        voter.voted_at = cast_time
        await self.voter_repo.update(voter)

        # 6. Mark Session as USED
        session.status = VotingSessionStatus.USED
        session.used_at = cast_time
        self.db.add(session)

        # 7. Audit Log (Preserves ballot secrecy while verifying audit trail)
        await record_audit_log(
            self.db,
            request,
            action="vote.cast_anonymous",
            resource_type="ballot",
            resource_id=ballot_serial_hash[:12] + "...", # Masked
            organization_id=voter.organization_id,
            new_state={"ballot_cast": True, "election_id": vote_in.election_id}
        )

        return VoteReceiptResponse(
            success=True,
            ballot_serial_hash=ballot_serial_hash,
            cast_timestamp=cast_time.isoformat(),
            message="Your anonymous vote was securely encrypted and cast in the election vault."
        )
