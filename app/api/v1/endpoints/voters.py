from typing import List, Optional

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_optional_current_user, require_permissions
from app.core.permissions import PermissionCode
from app.models.organization import Organization
from app.models.user import User
from app.schemas.common import APIResponse
from app.schemas.voter import (
    AudienceSplit,
    VoterCreate,
    VoterResponse,
    VoterUpdate,
    VoterVerificationRequest,
    VoterVerificationResponse,
)
from app.services.voter_service import VoterService

router = APIRouter(prefix="/voters", tags=["Voter Management"])


async def get_default_org_id(db: AsyncSession) -> str:
    org = (await db.execute(select(Organization).limit(1))).scalars().first()
    return org.id if org else "default_org"


@router.get("", response_model=List[VoterResponse])
@router.get("/", response_model=List[VoterResponse])
async def get_voters(
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve all voters in the campaign electoral roll."""
    org_id = current_user.organization_id if current_user else await get_default_org_id(db)
    service = VoterService(db)
    voters = await service.list_org_voters(organization_id=org_id)
    if not voters:
        voters = await service.list_org_voters(organization_id=None)
    return [VoterResponse.model_validate(v) for v in voters]


@router.get("/audience-split", response_model=AudienceSplit)
async def get_audience_split(
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get breakdown of voters reachable via WhatsApp vs SMS fallback."""
    org_id = current_user.organization_id if current_user else await get_default_org_id(db)
    service = VoterService(db)
    split = await service.get_audience_split(organization_id=org_id)
    return split if isinstance(split, AudienceSplit) else AudienceSplit(**split)


@router.post("", response_model=VoterResponse)
@router.post("/", response_model=VoterResponse)
async def create_voter(
    request: Request,
    voter_in: VoterCreate,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Enroll a new voter into the campaign roll."""
    service = VoterService(db)
    voter = await service.create_voter(request, voter_in, current_user)
    return VoterResponse.model_validate(voter)


@router.post("/batch", response_model=List[VoterResponse])
async def create_voters_batch(
    request: Request,
    voters_in: List[VoterCreate],
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Batch enroll voters (e.g. OCR roll upload or Excel import)."""
    service = VoterService(db)
    voters = await service.create_batch(request, voters_in, current_user)
    return [VoterResponse.model_validate(v) for v in voters]


@router.get("/{voter_id}", response_model=APIResponse[VoterResponse])
async def get_voter(
    voter_id: str,
    current_user: User = Depends(require_permissions(PermissionCode.VOTER_VIEW.value)),
    db: AsyncSession = Depends(get_db)
):
    service = VoterService(db)
    voter = await service.get_voter(voter_id)
    return APIResponse(data=VoterResponse.model_validate(voter))


@router.put("/{voter_id}", response_model=APIResponse[VoterResponse])
async def update_voter(
    request: Request,
    voter_id: str,
    voter_in: VoterUpdate,
    current_user: User = Depends(require_permissions(PermissionCode.VOTER_UPDATE.value)),
    db: AsyncSession = Depends(get_db)
):
    service = VoterService(db)
    voter = await service.update_voter(request, voter_id, voter_in, current_user)
    return APIResponse(
        success=True,
        message="Voter record updated.",
        data=VoterResponse.model_validate(voter)
    )


@router.post("/{voter_id}/verify", response_model=APIResponse[VoterVerificationResponse])
async def verify_voter(
    request: Request,
    voter_id: str,
    verify_in: VoterVerificationRequest,
    current_user: User = Depends(require_permissions(PermissionCode.VOTER_VERIFY.value)),
    db: AsyncSession = Depends(get_db)
):
    service = VoterService(db)
    resp = await service.verify_voter(request, voter_id, verify_in, current_user)
    return APIResponse(success=True, message=resp.message, data=resp)
