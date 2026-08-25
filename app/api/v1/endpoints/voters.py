from typing import List, Optional

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permissions
from app.core.permissions import PermissionCode
from app.models.organization import Organization
from app.models.user import User
from app.schemas.common import APIResponse
from app.schemas.voter import (
    AudienceSplit,
    VoterCreate,
    VoterBulkDeleteRequest,
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


from app.schemas.common import APIResponse, PaginatedResponse, PaginationMeta

@router.get("", response_model=List[VoterResponse])
@router.get("/", response_model=List[VoterResponse])
async def get_voters(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve all voters in the campaign electoral roll."""
    org_id = current_user.organization_id
    service = VoterService(db)
    voters = await service.list_org_voters(organization_id=org_id)
    return [VoterResponse.model_validate(v) for v in voters]


@router.get("/election/{election_id}", response_model=APIResponse[PaginatedResponse[VoterResponse]])
async def list_election_voters(
    election_id: str,
    page: int = 1,
    page_size: int = 50,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve voters for a specific election roll."""
    org_id = current_user.organization_id
    service = VoterService(db)
    voters = await service.list_org_voters(organization_id=org_id, election_id=election_id)

    if search:
        s = search.lower()
        voters = [
            v for v in voters
            if s in (v.first_name or "").lower()
            or s in (v.last_name or "").lower()
            or s in (v.name or "").lower()
            or s in (v.voter_id_number or "").lower()
            or s in (v.phone_number or "").lower()
            or s in (v.mobile or "").lower()
        ]

    total_items = len(voters)
    start = (page - 1) * page_size
    items = [VoterResponse.model_validate(v) for v in voters[start:start + page_size]]
    pagination = PaginationMeta(
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=max(1, (total_items + page_size - 1) // page_size),
        has_next=start + page_size < total_items,
        has_prev=page > 1
    )
    return APIResponse(
        success=True,
        message="Voters retrieved successfully.",
        data=PaginatedResponse(items=items, pagination=pagination, total=total_items)
    )


@router.get("/audience-split", response_model=AudienceSplit)
async def get_audience_split(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get breakdown of voters reachable via WhatsApp vs SMS fallback."""
    org_id = current_user.organization_id
    service = VoterService(db)
    split = await service.get_audience_split(organization_id=org_id)
    return split if isinstance(split, AudienceSplit) else AudienceSplit(**split)


@router.post("", response_model=VoterResponse)
@router.post("/", response_model=VoterResponse)
async def create_voter(
    request: Request,
    voter_in: VoterCreate,
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Batch enroll voters (e.g. OCR roll upload or Excel import)."""
    service = VoterService(db)
    voters = await service.create_batch(request, voters_in, current_user)
    return [VoterResponse.model_validate(v) for v in voters]


@router.delete("/bulk", response_model=APIResponse[dict])
async def delete_voters_bulk(
    request: Request,
    delete_in: VoterBulkDeleteRequest,
    current_user: User = Depends(require_permissions(PermissionCode.VOTER_UPDATE.value)),
    db: AsyncSession = Depends(get_db)
):
    service = VoterService(db)
    deleted_count = await service.delete_voters_bulk(request, [str(voter_id) for voter_id in delete_in.voter_ids], current_user)
    return APIResponse(
        success=True,
        message=f"Deleted {deleted_count} voter records.",
        data={"deleted_count": deleted_count}
    )


@router.get("/{voter_id}", response_model=APIResponse[VoterResponse])
async def get_voter(
    voter_id: str,
    current_user: User = Depends(require_permissions(PermissionCode.VOTER_VIEW.value)),
    db: AsyncSession = Depends(get_db)
):
    service = VoterService(db)
    voter = await service.get_voter(voter_id, organization_id=None if current_user.is_superuser else current_user.organization_id)
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


@router.delete("/{voter_id}", response_model=APIResponse[bool])
async def delete_voter(
    request: Request,
    voter_id: str,
    current_user: User = Depends(require_permissions(PermissionCode.VOTER_UPDATE.value)),
    db: AsyncSession = Depends(get_db)
):
    service = VoterService(db)
    await service.delete_voter(request, voter_id, current_user)
    return APIResponse(success=True, message="Voter record deleted.", data=True)


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
