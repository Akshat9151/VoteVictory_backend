from datetime import datetime, timezone, timedelta
from typing import List, Optional
from sqlalchemy import func, select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.area import Area, Booth
from app.models.candidate import Candidate
from app.models.data_collection import DataSubmission, SubmissionStatus
from app.models.election import Constituency, Election, ElectionStatus
from app.models.notification import NotificationCampaign, NotificationChannel
from app.models.polling_station import PollingStation
from app.models.voter import Voter, VoterStatus, VotingStatus
from app.models.volunteer import VolunteerProfile
from app.schemas.dashboard import (
    AdminDashboardResponse,
    AreaCollectionSummary,
    BoothCollectionSummary,
    CampaignChannelMetric,
    ElectionStatsCard,
    ExecutiveOverviewResponse,
    RecentActivityItem,
    StationTurnoutSummary,
    VoterTurnoutSummary,
    VolunteerPerformanceSummary,
)


def _normalize_dt(dt: Optional[datetime]) -> Optional[datetime]:
    if not dt:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


class DashboardService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_overview_dashboard(
        self,
        election_id: Optional[str] = None,
        organization_id: Optional[str] = None,
    ) -> ExecutiveOverviewResponse:
        # Base queries
        elec_stmt = select(Election)
        if organization_id:
            elec_stmt = elec_stmt.where(Election.organization_id == organization_id)
        if election_id:
            elec_stmt = elec_stmt.where(Election.id == election_id)

        elections = (await self.db.execute(elec_stmt)).scalars().all()
        total_elections = len(elections)
        active_elections = sum(1 for e in elections if e.status == ElectionStatus.LIVE)

        # Voters
        voter_stmt = select(Voter)
        if organization_id:
            voter_stmt = voter_stmt.where(Voter.organization_id == organization_id)
        if election_id:
            voter_stmt = voter_stmt.where(Voter.election_id == election_id)

        voters = (await self.db.execute(voter_stmt)).scalars().all()
        total_voters = len(voters)
        checked_in_voters = sum(1 for v in voters if v.is_checked_in)
        voted_voters = sum(1 for v in voters if v.voting_status == VotingStatus.VOTED)
        turnout_pct = round((voted_voters / total_voters * 100) if total_voters > 0 else 0.0, 2)

        # Polling stations
        station_stmt = select(PollingStation)
        if election_id:
            station_stmt = station_stmt.where(PollingStation.election_id == election_id)
        stations = (await self.db.execute(station_stmt)).scalars().all()
        total_stations = len(stations)
        active_stations = sum(1 for s in stations if s.status == "ACTIVE")

        # Candidates
        cand_stmt = select(Candidate)
        if election_id:
            cand_stmt = cand_stmt.where(Candidate.election_id == election_id)
        candidates = (await self.db.execute(cand_stmt)).scalars().all()
        total_candidates = len(candidates)
        approved_candidates = sum(1 for c in candidates if c.status == "APPROVED")

        # Volunteers
        vol_stmt = select(VolunteerProfile)
        if organization_id:
            vol_stmt = vol_stmt.where(VolunteerProfile.organization_id == organization_id)
        volunteers = (await self.db.execute(vol_stmt)).scalars().all()
        total_volunteers = len(volunteers)
        active_volunteers = sum(1 for v in volunteers if v.status == "ACTIVE")

        return ExecutiveOverviewResponse(
            total_elections=total_elections,
            active_elections=active_elections,
            total_voters=total_voters,
            checked_in_voters=checked_in_voters,
            total_votes_cast=voted_voters,
            overall_turnout_percentage=turnout_pct,
            total_polling_stations=total_stations,
            active_polling_stations=active_stations,
            total_candidates=total_candidates,
            approved_candidates=approved_candidates,
            total_volunteers=total_volunteers,
            active_volunteers=active_volunteers,
        )

    async def get_admin_dashboard(
        self,
        election_id: Optional[str] = None,
        organization_id: Optional[str] = None,
    ) -> AdminDashboardResponse:
        # Volunteers count & collection
        vol_stmt = select(VolunteerProfile).options(selectinload(VolunteerProfile.user))
        if organization_id:
            vol_stmt = vol_stmt.where(VolunteerProfile.organization_id == organization_id)
        volunteers = (await self.db.execute(vol_stmt)).scalars().all()
        total_volunteers = len(volunteers)
        active_volunteers = sum(1 for v in volunteers if v.status == "ACTIVE")

        # Data collection & quality
        sub_stmt = select(DataSubmission).options(selectinload(DataSubmission.volunteer))
        if organization_id:
            sub_stmt = sub_stmt.where(DataSubmission.organization_id == organization_id)
        submissions = (await self.db.execute(sub_stmt)).scalars().all()

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = now - timedelta(days=7)
        month_start = now - timedelta(days=30)

        total_collected = len(submissions)
        today_col = sum(1 for s in submissions if _normalize_dt(s.created_at) and _normalize_dt(s.created_at) >= today_start)
        week_col = sum(1 for s in submissions if _normalize_dt(s.created_at) and _normalize_dt(s.created_at) >= week_start)
        month_col = sum(1 for s in submissions if _normalize_dt(s.created_at) and _normalize_dt(s.created_at) >= month_start)

        approved_rec = sum(1 for s in submissions if s.status == SubmissionStatus.APPROVED)
        pending_rec = sum(1 for s in submissions if s.status in [SubmissionStatus.SUBMITTED, SubmissionStatus.UNDER_REVIEW])
        rejected_rec = sum(1 for s in submissions if s.status == SubmissionStatus.REJECTED)
        dup_rec = sum(1 for s in submissions if s.status == SubmissionStatus.DUPLICATE or s.is_flagged_duplicate)
        avg_quality = round(sum(s.quality_score for s in submissions) / total_collected, 2) if total_collected > 0 else 100.0

        # Campaigns
        camp_stmt = select(NotificationCampaign)
        if organization_id:
            camp_stmt = camp_stmt.where(NotificationCampaign.organization_id == organization_id)
        campaigns = (await self.db.execute(camp_stmt)).scalars().all()

        active_campaigns = sum(1 for c in campaigns if c.status in ["QUEUED", "PROCESSING"])
        sms_sent = sum(c.sent_count for c in campaigns if c.channel == NotificationChannel.SMS)
        whatsapp_sent = sum(c.sent_count for c in campaigns if c.channel == NotificationChannel.WHATSAPP)
        email_sent = sum(c.sent_count for c in campaigns if c.channel == NotificationChannel.EMAIL)
        ig_sent = sum(c.sent_count for c in campaigns if c.channel == NotificationChannel.INSTAGRAM)

        # Top volunteers
        sorted_vols = sorted(volunteers, key=lambda v: v.total_submissions or 0, reverse=True)[:5]
        top_vols = []
        for v in sorted_vols:
            achieve_pct = round((v.monthly_collection / v.monthly_target * 100) if v.monthly_target > 0 else 0.0, 2)
            top_vols.append(
                VolunteerPerformanceSummary(
                    volunteer_id=v.id,
                    volunteer_name=v.user.full_name if v.user else "Volunteer",
                    volunteer_code=v.volunteer_code,
                    collected_records=v.total_submissions or 0,
                    approved_records=v.approved_count or 0,
                    achievement_percentage=achieve_pct,
                )
            )

        # Area collection progress
        area_stmt = select(Area)
        if organization_id:
            area_stmt = area_stmt.where(Area.organization_id == organization_id)
        areas = (await self.db.execute(area_stmt)).scalars().all()
        area_summaries = []
        for a in areas[:5]:
            achieve_pct = round((a.collected_count / a.target * 100) if a.target > 0 else 0.0, 2)
            area_summaries.append(
                AreaCollectionSummary(
                    area_id=a.id,
                    area_name=a.name,
                    target=a.target,
                    collected=a.collected_count,
                    achievement_percentage=achieve_pct,
                    map_status=str(a.map_status),
                )
            )

        # Booth collection progress
        booth_stmt = select(Booth)
        if organization_id:
            booth_stmt = booth_stmt.where(Booth.organization_id == organization_id)
        booths = (await self.db.execute(booth_stmt)).scalars().all()
        booth_summaries = []
        for b in booths[:5]:
            achieve_pct = round((b.collected_count / b.target * 100) if b.target > 0 else 0.0, 2)
            booth_summaries.append(
                BoothCollectionSummary(
                    booth_id=b.id,
                    booth_number=b.booth_number,
                    booth_name=b.name,
                    target=b.target,
                    collected=b.collected_count,
                    achievement_percentage=achieve_pct,
                )
            )

        # Recent activities
        recent_subs = sorted(submissions, key=lambda s: _normalize_dt(s.created_at) or datetime.min, reverse=True)[:5]
        recent_activities = []
        for s in recent_subs:
            recent_activities.append(
                RecentActivityItem(
                    id=s.id,
                    activity_type="FIELD_DATA_COLLECTION",
                    title=f"Record collected for {s.citizen_name}",
                    description=f"Booth: {s.booth_no or 'N/A'}, Quality: {s.quality_score}%",
                    timestamp=_normalize_dt(s.created_at).isoformat() if s.created_at else "",
                    actor_name=s.volunteer.full_name if s.volunteer else "Field Volunteer",
                )
            )

        return AdminDashboardResponse(
            total_volunteers=total_volunteers,
            active_volunteers=active_volunteers,
            total_data_collected=total_collected,
            today_data_collected=today_col,
            weekly_data_collected=week_col,
            monthly_data_collected=month_col,
            approved_records=approved_rec,
            pending_records=pending_rec,
            rejected_records=rejected_rec,
            duplicate_records=dup_rec,
            average_data_quality=avg_quality,
            active_campaigns=active_campaigns,
            total_sms_sent=sms_sent,
            total_whatsapp_sent=whatsapp_sent,
            total_email_sent=email_sent,
            total_instagram_sent=ig_sent,
            top_performing_volunteers=top_vols,
            area_progress=area_summaries,
            booth_progress=booth_summaries,
            recent_activities=recent_activities,
        )
