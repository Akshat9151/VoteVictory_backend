from typing import List, Optional
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import get_current_user, get_optional_current_user, require_roles
from app.models.organization import Organization
from app.models.user import User
from app.schemas.booth import BoothResponse
from app.schemas.team import TeamMemberCreate, TeamMemberResponse
from app.schemas.volunteer import VolunteerResponse
from app.services.team_service import TeamService

router = APIRouter(tags=["Team & Volunteers"])


async def get_default_org_id(db: AsyncSession) -> str:
    from sqlalchemy import select
    org = (await db.execute(select(Organization).limit(1))).scalars().first()
    return org.id if org else "default_org"


@router.get("/team", response_model=List[TeamMemberResponse])
async def get_team_members(
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List campaign team members."""
    org_id = current_user.organization_id if current_user else await get_default_org_id(db)
    service = TeamService(db)
    return await service.get_team_members(organization_id=org_id)


@router.post("/team", response_model=TeamMemberResponse, dependencies=[Depends(require_roles(["superadmin", "admin"]))])
async def add_team_member(
    request: Request,
    member: TeamMemberCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Add a new member to the campaign team (Admin / Super Admin only)."""
    service = TeamService(db)
    client_ip = request.client.host if request.client else None
    return await service.add_team_member(
        data=member,
        organization_id=current_user.organization_id,
        user=current_user,
        ip_address=client_ip
    )


@router.get("/volunteers", response_model=List[VolunteerResponse])
async def get_volunteers(
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List active field volunteers with productivity metrics."""
    org_id = current_user.organization_id if current_user else await get_default_org_id(db)
    service = TeamService(db)
    return await service.get_volunteers(organization_id=org_id)


@router.get("/booths", response_model=List[BoothResponse])
async def get_booths(
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List campaign polling booths and coverage."""
    org_id = current_user.organization_id if current_user else await get_default_org_id(db)
    service = TeamService(db)
    return await service.get_booths(organization_id=org_id)
