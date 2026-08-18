from datetime import datetime, timezone

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit_log, record_security_event
from app.core.exceptions import (
    AppException,
    DoubleVotingException,
    ResourceNotFoundException,
    VoterEligibilityException,
)
from app.models.audit import SecuritySeverity
from app.models.user import User
from app.models.voter import VoterCheckin, VoterStatus, VotingStatus
from app.repositories.voter_repo import VoterRepository
from app.schemas.checkin import VoterCheckinRequest, VoterCheckinResponse


class CheckinService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.voter_repo = VoterRepository(db)

    async def checkin_voter(
        self,
        request: Request,
        checkin_in: VoterCheckinRequest,
        current_user: User
    ) -> VoterCheckinResponse:
        voter = await self.voter_repo.get_by_id(checkin_in.voter_id)
        if not voter:
            raise ResourceNotFoundException("Voter", checkin_in.voter_id)

        if voter.election_id != checkin_in.election_id:
            raise AppException(code="ELECTION_MISMATCH", message="Voter does not belong to the specified election.")

        # 1. Double Voting / Voted Check
        if voter.has_voted or voter.voting_status == VotingStatus.VOTED:
            await record_security_event(
                self.db,
                request,
                event_type="ALREADY_VOTED_CHECKIN_ATTEMPT",
                severity=SecuritySeverity.HIGH,
                organization_id=voter.organization_id,
                details={"voter_id": voter.id, "voter_epic": voter.voter_id_number}
            )
            raise DoubleVotingException(voter_id=voter.id)

        # 2. Eligibility & Suspension Check
        if voter.status in (VoterStatus.BLOCKED, VoterStatus.SUSPENDED, VoterStatus.INELIGIBLE):
            raise VoterEligibilityException(f"Voter status is '{voter.status.value}'. Check-in is barred.")

        # 3. Existing Checkin Check
        existing_checkin = await self.voter_repo.get_checkin(checkin_in.election_id, voter.id)
        if existing_checkin:
            raise AppException(
                code="ALREADY_CHECKED_IN",
                message=f"Voter was already checked in at {existing_checkin.checkin_time.strftime('%H:%M:%S')}."
            )

        # 4. Atomic Check-in insertion
        checkin = VoterCheckin(
            voter_id=voter.id,
            election_id=checkin_in.election_id,
            polling_station_id=checkin_in.polling_station_id,
            checked_in_by=current_user.id,
            checkin_method=checkin_in.checkin_method,
            checkin_time=datetime.now(timezone.utc),
            ip_address=request.client.host if request.client else None
        )
        self.db.add(checkin)

        # Update voter status
        voter.voting_status = VotingStatus.CHECKED_IN
        voter.status = VoterStatus.CHECKED_IN
        await self.voter_repo.update(voter)

        await record_audit_log(
            self.db,
            request,
            action="voter.checkin",
            resource_type="voter_checkin",
            resource_id=checkin.id,
            organization_id=voter.organization_id,
            current_user=current_user,
            new_state={"voter_id": voter.id, "station_id": checkin_in.polling_station_id}
        )

        return VoterCheckinResponse(
            id=checkin.id,
            voter_id=voter.id,
            election_id=checkin.election_id,
            polling_station_id=checkin.polling_station_id,
            checked_in_by=current_user.id,
            checkin_method=checkin.checkin_method,
            checkin_time=checkin.checkin_time,
            message="Voter successfully verified and checked in."
        )
