from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.area import Area, Booth
from app.models.data_collection import DataSubmission, SubmissionStatus
from app.models.notification import NotificationCampaign, NotificationChannel
from app.models.volunteer import VolunteerProfile
from app.models.voter import Voter, VotingStatus
from app.schemas.analytics import (
    AnalyticsChartsResponse,
    PerformanceDataPoint,
    TimeSeriesPoint,
)


class AnalyticsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_charts_data(
        self,
        organization_id: Optional[str] = None,
        election_id: Optional[str] = None,
    ) -> AnalyticsChartsResponse:
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        # 1. Daily Collection Trend (past 7 days)
        daily_points = []
        for i in range(6, -1, -1):
            day_date = now - timedelta(days=i)
            day_start = day_date.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_date.replace(hour=23, minute=59, second=59, microsecond=999999)

            stmt = select(func.count(DataSubmission.id)).where(
                DataSubmission.created_at >= day_start,
                DataSubmission.created_at <= day_end,
            )
            if organization_id:
                stmt = stmt.where(DataSubmission.organization_id == organization_id)
            if election_id:
                stmt = stmt.where(DataSubmission.election_id == election_id)

            count = (await self.db.execute(stmt)).scalar_one() or 0
            daily_points.append(
                TimeSeriesPoint(
                    timestamp=day_date.strftime("%Y-%m-%d"),
                    label=day_date.strftime("%a"),
                    value=count,
                    target=200,
                )
            )

        # 2. Weekly Trend (past 4 weeks)
        weekly_points = []
        for w in range(3, -1, -1):
            w_start = now - timedelta(weeks=w+1)
            w_end = now - timedelta(weeks=w)
            stmt = select(func.count(DataSubmission.id)).where(
                DataSubmission.created_at >= w_start,
                DataSubmission.created_at <= w_end,
            )
            if organization_id:
                stmt = stmt.where(DataSubmission.organization_id == organization_id)
            if election_id:
                stmt = stmt.where(DataSubmission.election_id == election_id)

            count = (await self.db.execute(stmt)).scalar_one() or 0
            weekly_points.append(
                TimeSeriesPoint(
                    timestamp=f"Week -{w}",
                    label=f"Wk {4-w}",
                    value=count,
                    target=1000,
                )
            )

        # 3. Monthly Trend (past 6 months)
        monthly_points = []
        for m in range(5, -1, -1):
            m_start = now - timedelta(days=30*(m+1))
            m_end = now - timedelta(days=30*m)
            stmt = select(func.count(DataSubmission.id)).where(
                DataSubmission.created_at >= m_start,
                DataSubmission.created_at <= m_end,
            )
            if organization_id:
                stmt = stmt.where(DataSubmission.organization_id == organization_id)
            if election_id:
                stmt = stmt.where(DataSubmission.election_id == election_id)

            count = (await self.db.execute(stmt)).scalar_one() or 0
            monthly_points.append(
                TimeSeriesPoint(
                    timestamp=f"Month -{m}",
                    label=f"M-{m+1}",
                    value=count,
                    target=4000,
                )
            )

        # 4. Volunteer Performance
        vol_stmt = select(VolunteerProfile).options(selectinload(VolunteerProfile.user))
        if organization_id:
            vol_stmt = vol_stmt.where(VolunteerProfile.organization_id == organization_id)
        if election_id:
            vol_stmt = vol_stmt.where(VolunteerProfile.election_id == election_id)
        vols = (await self.db.execute(vol_stmt)).scalars().all()

        vol_performance = []
        for v in vols[:10]:
            achieve_pct = round((v.monthly_collection / v.monthly_target * 100) if v.monthly_target > 0 else 0.0, 2)
            vol_performance.append(
                PerformanceDataPoint(
                    id=v.id,
                    name=v.user.full_name if v.user else "Volunteer",
                    target=v.monthly_target,
                    collected=v.monthly_collection,
                    approved=v.approved_count,
                    rejected=v.rejected_count,
                    duplicate=v.duplicate_count,
                    achievement_percentage=achieve_pct,
                )
            )

        # 5. Area Performance
        area_stmt = select(Area)
        if organization_id:
            area_stmt = area_stmt.where(Area.organization_id == organization_id)
        areas = (await self.db.execute(area_stmt)).scalars().all()
        area_performance = []
        for a in areas[:10]:
            achieve_pct = round((a.collected_count / a.target * 100) if a.target > 0 else 0.0, 2)
            area_performance.append(
                PerformanceDataPoint(
                    id=a.id,
                    name=a.name,
                    target=a.target,
                    collected=a.collected_count,
                    approved=a.collected_count,
                    rejected=0,
                    duplicate=0,
                    achievement_percentage=achieve_pct,
                )
            )

        # 6. Booth Performance
        booth_stmt = select(Booth)
        if organization_id:
            booth_stmt = booth_stmt.where(Booth.organization_id == organization_id)
        booths = (await self.db.execute(booth_stmt)).scalars().all()
        booth_performance = []
        for b in booths[:10]:
            achieve_pct = round((b.collected_count / b.target * 100) if b.target > 0 else 0.0, 2)
            booth_performance.append(
                PerformanceDataPoint(
                    id=b.id,
                    name=f"{b.booth_number} - {b.name}",
                    target=b.target,
                    collected=b.collected_count,
                    approved=b.collected_count,
                    rejected=0,
                    duplicate=0,
                    achievement_percentage=achieve_pct,
                )
            )

        # 7. Data Quality Distribution
        sub_stmt = select(DataSubmission)
        if organization_id:
            sub_stmt = sub_stmt.where(DataSubmission.organization_id == organization_id)
        if election_id:
            sub_stmt = sub_stmt.where(DataSubmission.election_id == election_id)

        all_subs = (await self.db.execute(sub_stmt)).scalars().all()
        app_count = sum(1 for s in all_subs if s.status == SubmissionStatus.APPROVED)
        rej_count = sum(1 for s in all_subs if s.status == SubmissionStatus.REJECTED)
        dup_count = sum(1 for s in all_subs if s.status == SubmissionStatus.DUPLICATE or s.is_flagged_duplicate)
        valid_count = sum(1 for s in all_subs if s.quality_score >= 80.0)
        invalid_count = sum(1 for s in all_subs if s.quality_score < 50.0)

        quality_dist = {
            "valid": valid_count,
            "invalid": invalid_count,
            "duplicate": dup_count,
            "approved": app_count,
            "rejected": rej_count,
        }

        # 8. Voter Funnel
        voter_stmt = select(Voter)
        if organization_id:
            voter_stmt = voter_stmt.where(Voter.organization_id == organization_id)
        if election_id:
            voter_stmt = voter_stmt.where(Voter.election_id == election_id)
        all_voters = (await self.db.execute(voter_stmt)).scalars().all()
        total_voters = len(all_voters)
        checked_in = sum(1 for v in all_voters if v.is_checked_in)
        voted = sum(1 for v in all_voters if v.voting_status == VotingStatus.VOTED)

        voter_funnel = {
            "registered": total_voters,
            "verified": total_voters,
            "checked_in": checked_in,
            "voted": voted,
        }

        # 9. Communication Delivery Rates
        camp_stmt = select(NotificationCampaign)
        if organization_id:
            camp_stmt = camp_stmt.where(NotificationCampaign.organization_id == organization_id)
        all_camps = (await self.db.execute(camp_stmt)).scalars().all()

        comm_rates: Dict[str, Dict[str, int]] = {
            "sms": {"sent": sum(c.sent_count for c in all_camps if c.channel == NotificationChannel.SMS), "delivered": sum(c.delivered_count for c in all_camps if c.channel == NotificationChannel.SMS)},
            "whatsapp": {"sent": sum(c.sent_count for c in all_camps if c.channel == NotificationChannel.WHATSAPP), "delivered": sum(c.delivered_count for c in all_camps if c.channel == NotificationChannel.WHATSAPP)},
            "email": {"sent": sum(c.sent_count for c in all_camps if c.channel == NotificationChannel.EMAIL), "delivered": sum(c.delivered_count for c in all_camps if c.channel == NotificationChannel.EMAIL)},
            "instagram": {"sent": sum(c.sent_count for c in all_camps if c.channel == NotificationChannel.INSTAGRAM), "delivered": sum(c.delivered_count for c in all_camps if c.channel == NotificationChannel.INSTAGRAM)},
        }

        return AnalyticsChartsResponse(
            daily_collection_trend=daily_points,
            weekly_collection_trend=weekly_points,
            monthly_collection_trend=monthly_points,
            volunteer_performance=vol_performance,
            area_performance=area_performance,
            booth_performance=booth_performance,
            data_quality_distribution=quality_dist,
            voter_verification_funnel=voter_funnel,
            communication_delivery_rates=comm_rates,
            election_turnout_by_station=[],
        )
