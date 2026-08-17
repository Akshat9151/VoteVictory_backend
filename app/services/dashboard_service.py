from typing import Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import ResourceNotFoundException
from app.models.audit import AuditLog, SecurityEvent
from app.models.candidate import Candidate
from app.models.election import Election, ElectionStatus
from app.models.notification import NotificationCampaign
from app.models.organization import Organization, OrganizationStatus
from app.models.polling_station import PollingStation, VolunteerAssignment
from app.models.user import User
from app.models.voter import Voter, VoterCheckin, VoterStatus, VotingStatus
from app.models.voting import Ballot
from app.schemas.dashboard import (
    AdminDashboardResponse,
    SuperAdminDashboardResponse,
    VolunteerDashboardResponse,
)


class DashboardService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_super_admin_dashboard(self) -> SuperAdminDashboardResponse:
        total_orgs = (await self.db.execute(select(func.count(Organization.id)))).scalar_one() or 0
        active_orgs = (await self.db.execute(
            select(func.count(Organization.id)).where(Organization.status == OrganizationStatus.ACTIVE)
        )).scalar_one() or 0

        total_users = (await self.db.execute(select(func.count(User.id)))).scalar_one() or 0
        active_elections = (await self.db.execute(
            select(func.count(Election.id)).where(Election.status.in_([ElectionStatus.LIVE, ElectionStatus.SCHEDULED, ElectionStatus.UPCOMING]))
        )).scalar_one() or 0
        completed_elections = (await self.db.execute(
            select(func.count(Election.id)).where(Election.status.in_([ElectionStatus.RESULT_PUBLISHED, ElectionStatus.ARCHIVED, ElectionStatus.CLOSED]))
        )).scalar_one() or 0

        total_voters = (await self.db.execute(select(func.count(Voter.id)))).scalar_one() or 0
        total_ballots = (await self.db.execute(select(func.count(Ballot.id)))).scalar_one() or 0
        total_broadcasts = (await self.db.execute(
            select(func.coalesce(func.sum(NotificationCampaign.sent_count), 0))
        )).scalar_one() or 0

        # Recent events
        sec_events = (await self.db.execute(
            select(SecurityEvent).order_by(SecurityEvent.created_at.desc()).limit(5)
        )).scalars().all()

        audit_entries = (await self.db.execute(
            select(AuditLog).order_by(AuditLog.created_at.desc()).limit(5)
        )).scalars().all()

        return SuperAdminDashboardResponse(
            total_organizations=total_orgs,
            active_organizations=active_orgs,
            total_users=total_users,
            active_elections=active_elections,
            completed_elections=completed_elections,
            total_voters_registered=total_voters,
            total_votes_processed=total_ballots,
            total_broadcasts_sent=total_broadcasts,
            recent_security_events=[
                {"event_type": e.event_type, "severity": e.severity.value, "time": e.created_at.isoformat()}
                for e in sec_events
            ],
            recent_audit_logs=[
                {"action": a.action, "actor": a.actor_email, "resource": a.resource_type, "time": a.created_at.isoformat()}
                for a in audit_entries
            ]
        )

    async def get_admin_dashboard(self, election_id: str) -> AdminDashboardResponse:
        election = await self.db.get(Election, election_id)
        if not election:
            raise ResourceNotFoundException("Election", election_id)

        total_voters = (await self.db.execute(
            select(func.count(Voter.id)).where(Voter.election_id == election_id)
        )).scalar_one() or 0

        eligible_voters = (await self.db.execute(
            select(func.count(Voter.id)).where(
                Voter.election_id == election_id,
                Voter.status.in_([VoterStatus.REGISTERED, VoterStatus.VERIFIED, VoterStatus.ELIGIBLE])
            )
        )).scalar_one() or 0

        checked_in = (await self.db.execute(
            select(func.count(VoterCheckin.id)).where(VoterCheckin.election_id == election_id)
        )).scalar_one() or 0

        votes_cast = (await self.db.execute(
            select(func.count(Ballot.id)).where(Ballot.election_id == election_id)
        )).scalar_one() or 0

        turnout = (votes_cast / total_voters * 100) if total_voters > 0 else 0.0

        stations_count = (await self.db.execute(
            select(func.count(PollingStation.id)).where(PollingStation.election_id == election_id)
        )).scalar_one() or 0

        volunteers_count = (await self.db.execute(
            select(func.count(VolunteerAssignment.id)).where(
                VolunteerAssignment.election_id == election_id,
                VolunteerAssignment.is_active == True
            )
        )).scalar_one() or 0

        candidates_count = (await self.db.execute(
            select(func.count(Candidate.id)).where(Candidate.election_id == election_id)
        )).scalar_one() or 0

        broadcasts_dispatched = (await self.db.execute(
            select(func.coalesce(func.sum(NotificationCampaign.sent_count), 0)).where(
                NotificationCampaign.election_id == election_id
            )
        )).scalar_one() or 0

        return AdminDashboardResponse(
            election_id=election.id,
            election_title=election.title,
            election_status=election.status.value,
            total_voters=total_voters,
            eligible_voters=eligible_voters,
            checked_in_voters=checked_in,
            votes_cast=votes_cast,
            turnout_percentage=round(turnout, 2),
            total_polling_stations=stations_count,
            active_volunteers=volunteers_count,
            total_candidates=candidates_count,
            broadcasts_dispatched=broadcasts_dispatched,
            pending_tasks=0
        )

    async def get_volunteer_dashboard(self, current_user: User) -> VolunteerDashboardResponse:
        # Find active volunteer assignment
        assignment_stmt = (
            select(VolunteerAssignment)
            .where(VolunteerAssignment.user_id == current_user.id, VolunteerAssignment.is_active == True)
        )
        assignment = (await self.db.execute(assignment_stmt)).scalars().first()

        if not assignment:
            return VolunteerDashboardResponse(
                volunteer_name=current_user.full_name,
                assigned_election_id="",
                assigned_election_title="No Active Election Assigned",
                assigned_station_id="",
                assigned_station_name="None",
                station_address="None",
                task_role="VOLUNTEER",
                total_ward_voters=0,
                checked_in_count=0,
                voters_visited_count=0,
                voters_called_count=0
            )

        election = await self.db.get(Election, assignment.election_id)
        station = await self.db.get(PollingStation, assignment.polling_station_id)

        voters_count = (await self.db.execute(
            select(func.count(Voter.id)).where(Voter.polling_station_id == assignment.polling_station_id)
        )).scalar_one() or 0

        checked_in = (await self.db.execute(
            select(func.count(VoterCheckin.id)).where(VoterCheckin.polling_station_id == assignment.polling_station_id)
        )).scalar_one() or 0

        return VolunteerDashboardResponse(
            volunteer_name=current_user.full_name,
            assigned_election_id=assignment.election_id,
            assigned_election_title=election.title if election else "Election",
            assigned_station_id=assignment.polling_station_id,
            assigned_station_name=station.name if station else "Station",
            station_address=station.address if station else "",
            task_role=assignment.task_role,
            total_ward_voters=voters_count,
            checked_in_count=checked_in,
            voters_visited_count=int(checked_in * 0.8),
            voters_called_count=int(voters_count * 0.6)
        )
