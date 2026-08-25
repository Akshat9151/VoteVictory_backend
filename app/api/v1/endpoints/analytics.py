from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.data_collection import DataSubmission
from app.models.design_template import DesignTemplate
from app.models.organization import Organization
from app.models.saved_design import SavedDesign
from app.models.team import Volunteer
from app.models.user import User, UserRole
from app.models.volunteer import VolunteerProfile
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
    # 1. Fetch real voters scoped strictly to election_id if provided
    voter_stmt = select(Voter)
    if election_id:
        voter_stmt = voter_stmt.where(Voter.election_id == election_id)
    elif org_id:
        voter_stmt = voter_stmt.where(Voter.organization_id == org_id)
    voters = list((await db.execute(voter_stmt)).scalars().all())

    # 2. Channel delivery calculation based on real voters
    whatsapp_count = sum(
        1 for v in voters
        if (getattr(v, "channel", None) == "WhatsApp" or getattr(v, "channel", None) is None)
        and (getattr(v, "mobile", None) or getattr(v, "phone_number", None))
    )
    sms_count = sum(
        1 for v in voters
        if getattr(v, "channel", None) == "SMS Only"
        or (not getattr(v, "mobile", None) and not getattr(v, "phone_number", None))
    )
    total_voters = len(voters)
    unreachable_count = sum(
        1 for v in voters
        if not getattr(v, "mobile", None) and not getattr(v, "phone_number", None)
    )

    channel_items = [
        ChannelDeliveryItem(channel="WhatsApp Verified", count=whatsapp_count, color="#059669"),
        ChannelDeliveryItem(channel="SMS / Call Reach", count=max(0, sms_count - unreachable_count), color="#0284c7"),
        ChannelDeliveryItem(channel="Missing Contact", count=unreachable_count, color="#94a3b8"),
    ]

    # 3. Ward coverage from real voters
    ward_items = [
        WardCoverageItem(
            ward=f"Ward {ward}" if not ward.lower().startswith("ward") and ward.isdigit() else ward,
            percentage=round((reached / total) * 100) if total else 0,
        )
        for ward, total, reached in _ward_reach(voters)
    ]

    # 4. Material production from real SavedDesign records
    design_stmt = select(SavedDesign)
    if election_id:
        design_stmt = design_stmt.where(SavedDesign.election_id == election_id)
    elif org_id:
        design_stmt = design_stmt.where(SavedDesign.organization_id == org_id)
    saved_designs = list((await db.execute(design_stmt)).scalars().all())

    posters_count = sum(1 for d in saved_designs if "poster" in (d.title or "").lower())
    pamphlets_count = sum(1 for d in saved_designs if "pamphlet" in (d.title or "").lower())
    banners_count = sum(1 for d in saved_designs if "banner" in (d.title or "").lower() or "hoarding" in (d.title or "").lower())
    cards_count = sum(1 for d in saved_designs if "id" in (d.title or "").lower() or "card" in (d.title or "").lower())
    other_designs = max(0, len(saved_designs) - (posters_count + pamphlets_count + banners_count + cards_count))

    material_items = [
        MaterialPrintItem(type="Campaign Posters", count=posters_count if len(saved_designs) > 0 else len(saved_designs)),
        MaterialPrintItem(type="Pamphlets & Flyers", count=pamphlets_count),
        MaterialPrintItem(type="Hoardings & Banners", count=banners_count),
        MaterialPrintItem(type="Worker ID Badges", count=cards_count if cards_count > 0 else other_designs),
    ]

    # 5. Volunteer productivity from real VolunteerProfile and User records
    vol_stmt = select(VolunteerProfile).options(selectinload(VolunteerProfile.user))
    if election_id:
        vol_stmt = vol_stmt.where(VolunteerProfile.election_id == election_id)
    elif org_id:
        vol_stmt = vol_stmt.where(VolunteerProfile.organization_id == org_id)
    vol_profiles = list((await db.execute(vol_stmt)).scalars().all())

    vol_productivity: list[VolunteerProductivityItem] = []
    for vp in vol_profiles[:10]:
        vol_name = vp.user.full_name if vp.user else "Field Volunteer"
        slips = vp.total_submissions or vp.monthly_collection or 0
        calls = vp.approved_count or 0
        vol_productivity.append(
            VolunteerProductivityItem(
                name=vol_name,
                slips=slips,
                calls=calls,
            )
        )

    # Fallback to team.Volunteer if no profiles found
    if not vol_productivity:
        team_vol_stmt = select(Volunteer)
        if org_id:
            team_vol_stmt = team_vol_stmt.where(Volunteer.organization_id == org_id)
        team_vols = list((await db.execute(team_vol_stmt)).scalars().all())
        for tv in team_vols[:10]:
            vol_productivity.append(
                VolunteerProductivityItem(
                    name=tv.name,
                    slips=getattr(tv, "slipsDistributed", 0) or 0,
                    calls=getattr(tv, "callsMade", 0) or 0,
                )
            )

    return AnalyticsData(
        wardCoverage=ward_items,
        channelDelivery=channel_items,
        materialPrints=material_items,
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
        ward = (
            getattr(voter, "ward_name", None)
            or getattr(voter, "ward", None)
            or "General Ward"
        )
        grouped.setdefault(str(ward).strip(), []).append(voter)
    return [
        (
            ward,
            len(ward_voters),
            sum(1 for voter in ward_voters if (getattr(voter, "mobile", None) or getattr(voter, "phone_number", None)))
        )
        for ward, ward_voters in sorted(grouped.items())
    ]
