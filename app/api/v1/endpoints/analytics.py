from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.organization import Organization
from app.models.team import Volunteer
from app.models.user import User
from app.models.voter import Voter
from app.schemas.analytics import (
    AnalyticsChartsResponse,
    AnalyticsData,
    ChannelDeliveryItem,
    MaterialPrintItem,
    VolunteerProductivityItem,
    WardCoverageItem,
)
from app.schemas.common import APIResponse
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Operational Analytics & Charts Engine"])


async def get_default_org_id(db: AsyncSession) -> str:
    org = (await db.execute(select(Organization).limit(1))).scalars().first()
    return org.id if org else "default_org"


async def build_analytics_data(db: AsyncSession, org_id: Optional[str] = None, election_id: Optional[str] = None) -> AnalyticsData:
    # Fetch volunteers for productivity
    vol_stmt = select(Volunteer)
    if org_id:
        vol_stmt = vol_stmt.where(Volunteer.organization_id == org_id)
    volunteers = list((await db.execute(vol_stmt)).scalars().all())

    # Fetch voters for channel delivery
    voter_stmt = select(Voter)
    if org_id:
        voter_stmt = voter_stmt.where(Voter.organization_id == org_id)
    if election_id:
        voter_stmt = voter_stmt.where(Voter.election_id == election_id)
    voters = list((await db.execute(voter_stmt)).scalars().all())

    whatsapp_count = sum(1 for v in voters if getattr(v, "channel", None) == "WhatsApp" and getattr(v, "mobile", None))
    sms_count = sum(1 for v in voters if getattr(v, "channel", None) != "WhatsApp" or not getattr(v, "mobile", None))

    vol_productivity = [
        VolunteerProductivityItem(
            name=v.name,
            slips=getattr(v, "slipsDistributed", 0) or 0,
            calls=getattr(v, "callsMade", 0) or 0,
        )
        for v in volunteers
    ]

    return AnalyticsData(
        wardCoverage=[
            WardCoverageItem(
                ward=ward or "Unknown",
                percentage=round((reached / total) * 100) if total else 0,
            )
            for ward, total, reached in _ward_reach(voters)
        ],
        channelDelivery=[
            ChannelDeliveryItem(channel="WhatsApp", count=whatsapp_count, color="#059669"),
            ChannelDeliveryItem(channel="SMS Fallback", count=sms_count, color="#0284c7"),
            ChannelDeliveryItem(channel="Failed", count=0, color="#e11d48"),
        ],
        materialPrints=[],
        volunteerProductivity=vol_productivity,
    )


@router.get("/charts", response_model=APIResponse[AnalyticsChartsResponse])
async def get_analytics_charts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve time-series charts, area/volunteer performance and funnels."""
    org_id = current_user.organization_id
    service = AnalyticsService(db)
    charts = await service.get_charts_data(organization_id=org_id)
    return APIResponse(success=True, data=charts)


@router.get("/election/{election_id}/turnout", response_model=APIResponse[AnalyticsData])
async def get_election_turnout_analytics(
    election_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve election turnout analytics breakdown for the analytics page."""
    org_id = current_user.organization_id
    data = await build_analytics_data(db, org_id, election_id=election_id)
    return APIResponse(
        success=True,
        message="Turnout analytics retrieved.",
        data=data,
    )


@router.get("", response_model=AnalyticsData)
@router.get("/", response_model=AnalyticsData)
async def get_analytics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve operational analytics, ward coverage, channel delivery and volunteer productivity."""
    org_id = current_user.organization_id
    return await build_analytics_data(db, org_id)


def _ward_reach(voters: list[Voter]) -> list[tuple[str, int, int]]:
    grouped: dict[str, list[Voter]] = {}
    for voter in voters:
        ward = getattr(voter, "ward_name", None) or getattr(voter, "ward", None) or "Unknown"
        grouped.setdefault(ward, []).append(voter)
    return [
        (ward, len(ward_voters), sum(1 for voter in ward_voters if getattr(voter, "mobile", None) or getattr(voter, "phone_number", None)))
        for ward, ward_voters in sorted(grouped.items())
    ]
