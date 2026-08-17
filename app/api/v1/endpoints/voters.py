from typing import Optional
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import require_permissions
from app.core.permissions import PermissionCode
from app.models.user import User
from app.models.voter import Voter, VoterStatus, VotingStatus
from app.schemas.common import APIResponse, PaginatedResponse
from app.schemas.voter import (
    VoterCreate,
    VoterFilterParams,
    VoterResponse,
    VoterUpdate,
    VoterVerificationRequest,
    VoterVerificationResponse,
)
from app.services.voter_service import VoterService

router = APIRouter(prefix="/voters", tags=["Voter Management"])


@router.get("/election/{election_id}", response_model=APIResponse[PaginatedResponse[VoterResponse]])
async def list_voters(
    election_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    status: Optional[VoterStatus] = None,
    voting_status: Optional[VotingStatus] = None,
    constituency_id: Optional[str] = None,
    polling_station_id: Optional[str] = None,
    ward_name: Optional[str] = None,
    has_voted: Optional[bool] = None,
    current_user: User = Depends(require_permissions(PermissionCode.VOTER_VIEW.value)),
    db: AsyncSession = Depends(get_db)
):
    service = VoterService(db)
    filters = VoterFilterParams(
        search=search,
        status=status,
        voting_status=voting_status,
        constituency_id=constituency_id,
        polling_station_id=polling_station_id,
        ward_name=ward_name,
        has_voted=has_voted
    )
    voters, pagination = await service.list_voters(
        election_id=election_id,
        current_user=current_user,
        filters=filters,
        page=page,
        page_size=page_size
    )
    items = [VoterResponse.model_validate(v) for v in voters]
    return APIResponse(data=PaginatedResponse(items=items, pagination=pagination))


@router.post("/", response_model=APIResponse[VoterResponse])
async def create_voter(
    request: Request,
    voter_in: VoterCreate,
    current_user: User = Depends(require_permissions(PermissionCode.VOTER_CREATE.value)),
    db: AsyncSession = Depends(get_db)
):
    service = VoterService(db)
    voter = await service.create_voter(request, voter_in, current_user)
    return APIResponse(
        success=True,
        message="Voter enrolled in electoral roll.",
        data=VoterResponse.model_validate(voter)
    )


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
