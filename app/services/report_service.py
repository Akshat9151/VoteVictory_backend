import csv
import io
from typing import Any, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.data_collection import DataSubmission
from app.models.election import Election
from app.models.notification import NotificationCampaign
from app.models.volunteer import VolunteerProfile
from app.schemas.report import (
    CampaignReportRow,
    DataReportRow,
    ElectionReportSummary,
    VolunteerReportRow,
)


class ReportService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_volunteer_report(self, organization_id: str) -> List[VolunteerReportRow]:
        stmt = (
            select(VolunteerProfile)
            .options(selectinload(VolunteerProfile.user))
            .where(VolunteerProfile.organization_id == organization_id)
        )
        results = (await self.db.execute(stmt)).scalars().all()

        report = []
        for p in results:
            achieve_pct = round((p.monthly_collection / p.monthly_target * 100) if p.monthly_target > 0 else 0.0, 2)
            report.append(
                VolunteerReportRow(
                    volunteer_name=p.user.full_name if p.user else "Volunteer",
                    volunteer_code=p.volunteer_code,
                    area_name=p.area_id,
                    booth_number=p.booth_id,
                    daily_target=p.daily_target,
                    monthly_target=p.monthly_target,
                    collected_count=p.total_submissions,
                    approved_count=p.approved_count,
                    rejected_count=p.rejected_count,
                    duplicate_count=p.duplicate_count,
                    achievement_percentage=achieve_pct,
                )
            )
        return report

    async def get_data_report(self, organization_id: str, limit: int = 200) -> List[DataReportRow]:
        stmt = (
            select(DataSubmission)
            .options(selectinload(DataSubmission.volunteer))
            .where(DataSubmission.organization_id == organization_id)
            .limit(limit)
        )
        results = (await self.db.execute(stmt)).scalars().all()

        return [
            DataReportRow(
                submission_id=s.id,
                citizen_name=s.citizen_name,
                mobile=s.mobile,
                voter_card_number=s.voter_card_number,
                area_name=s.area_id,
                booth_no=s.booth_no,
                volunteer_name=s.volunteer.full_name if s.volunteer else None,
                status=str(s.status),
                quality_score=s.quality_score,
                submitted_at=s.created_at,
            )
            for s in results
        ]

    async def get_election_report(self, election_id: str) -> Optional[ElectionReportSummary]:
        stmt = (
            select(Election)
            .options(
                selectinload(Election.voters),
                selectinload(Election.polling_stations),
                selectinload(Election.candidates),
            )
            .where(Election.id == election_id)
        )
        election = (await self.db.execute(stmt)).scalar_one_or_none()
        if not election:
            return None

        total_voters = len(election.voters)
        eligible = sum(1 for v in election.voters if v.status == "ACTIVE")
        checked_in = sum(1 for v in election.voters if v.voting_status in ["CHECKED_IN", "VOTED"])
        votes = sum(1 for v in election.voters if v.voting_status == "VOTED")
        turnout = round((votes / total_voters * 100) if total_voters > 0 else 0.0, 2)

        return ElectionReportSummary(
            election_title=election.title,
            status=str(election.status),
            total_voters=total_voters,
            eligible_voters=eligible,
            checked_in_voters=checked_in,
            total_votes_cast=votes,
            turnout_percentage=turnout,
            total_stations=len(election.polling_stations),
            total_candidates=len(election.candidates),
        )

    async def get_campaign_report(self, organization_id: str) -> List[CampaignReportRow]:
        stmt = select(NotificationCampaign).where(NotificationCampaign.organization_id == organization_id)
        results = (await self.db.execute(stmt)).scalars().all()

        report = []
        for c in results:
            rate = round((c.delivered_count / c.sent_count * 100) if c.sent_count > 0 else 0.0, 2)
            report.append(
                CampaignReportRow(
                    campaign_name=c.name,
                    channel=str(c.channel),
                    audience_type=c.target_audience_type,
                    total_recipients=c.total_recipients,
                    sent_count=c.sent_count,
                    delivered_count=c.delivered_count,
                    failed_count=c.failed_count,
                    delivery_rate=rate,
                )
            )
        return report

    def export_to_csv(self, headers: List[str], rows: List[List[Any]]) -> str:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(headers)
        for row in rows:
            writer.writerow(row)
        return output.getvalue()
