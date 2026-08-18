from typing import List, Optional
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import get_current_user, get_optional_current_user, require_roles
from app.models.organization import Organization
from app.models.user import User
from app.schemas.volunteer_voter import (
    VolunteerVoterCreate,
    VolunteerVoterResponse,
    VolunteerVoterStatusUpdate,
)
from app.services.volunteer_voter_service import VolunteerVoterService

router = APIRouter(prefix="/volunteer-voters", tags=["Volunteer Canvassing"])


async def get_default_org_id(db: AsyncSession) -> str:
    from sqlalchemy import select
    org = (await db.execute(select(Organization).limit(1))).scalars().first()
    return org.id if org else "default_org"


@router.get("", response_model=List[VolunteerVoterResponse])
async def get_volunteer_voters(
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve voter canvassing records assigned to volunteers."""
    org_id = current_user.organization_id if current_user else await get_default_org_id(db)
    service = VolunteerVoterService(db)
    return await service.get_volunteer_voters(organization_id=org_id)


@router.post("", response_model=VolunteerVoterResponse, dependencies=[Depends(require_roles(["superadmin", "admin", "volunteer"]))])
async def add_volunteer_voter(
    request: Request,
    voter: VolunteerVoterCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Add a new canvassing voter entry from field duty."""
    service = VolunteerVoterService(db)
    client_ip = request.client.host if request.client else None
    return await service.add_volunteer_voter(
        data=voter,
        organization_id=current_user.organization_id,
        user=current_user,
        ip_address=client_ip
    )


@router.patch("/{id}/status", response_model=VolunteerVoterResponse, dependencies=[Depends(require_roles(["superadmin", "admin", "volunteer"]))])
async def update_volunteer_voter_status(
    id: str,
    status_update: VolunteerVoterStatusUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update door-to-door canvassing status (Visited/Called/Pending) and slip handover."""
    service = VolunteerVoterService(db)
    client_ip = request.client.host if request.client else None
    return await service.update_status(
        id=id,
        data=status_update,
        organization_id=current_user.organization_id,
        user=current_user,
        ip_address=client_ip
    )
