from typing import Optional
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import require_permissions
from app.core.permissions import PermissionCode
from app.models.candidate import Candidate, CandidateStatus
from app.models.user import User
from app.schemas.candidate import (
    CandidateCreate,
    CandidateDocumentResponse,
    CandidateResponse,
    CandidateStatusUpdateRequest,
    CandidateUpdate,
)
from app.schemas.common import APIResponse, PaginatedResponse
from app.services.candidate_service import CandidateService

router = APIRouter(prefix="/candidates", tags=["Candidate Management"])


from sqlalchemy import inspect

def serialize_candidate(c: Candidate) -> CandidateResponse:
    docs = []
    insp = inspect(c)
    if "documents" in insp.dict and c.documents:
        docs = [
            CandidateDocumentResponse(
                id=d.id,
                document_type=d.document_type,
                file_name=d.file_name,
                file_url=d.file_url,
                verification_status=d.verification_status,
                created_at=d.created_at
            )
            for d in c.documents
        ]
    return CandidateResponse(
        id=c.id,
        election_id=c.election_id,
        position_id=c.position_id,
        constituency_id=c.constituency_id,
        full_name=c.full_name,
        candidate_id_number=c.candidate_id_number,
        party_name=c.party_name,
        party_symbol_url=c.party_symbol_url,
        photo_url=c.photo_url,
        phone=c.phone,
        email=c.email,
        manifesto=c.manifesto,
        status=c.status,
        display_order=c.display_order,
        rejection_reason=c.rejection_reason,
        approved_by=c.approved_by,
        documents=docs,
        created_at=c.created_at,
        updated_at=c.updated_at
    )


@router.get("/election/{election_id}", response_model=APIResponse[PaginatedResponse[CandidateResponse]])
async def list_candidates(
    election_id: str,
    position_id: Optional[str] = None,
    constituency_id: Optional[str] = None,
    status: Optional[CandidateStatus] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(require_permissions(PermissionCode.CANDIDATE_VIEW.value)),
    db: AsyncSession = Depends(get_db)
):
    service = CandidateService(db)
    candidates, pagination = await service.list_candidates(
        election_id=election_id,
        position_id=position_id,
        constituency_id=constituency_id,
        status=status,
        page=page,
        page_size=page_size
    )
    items = [serialize_candidate(c) for c in candidates]
    return APIResponse(data=PaginatedResponse(items=items, pagination=pagination))


@router.post("/", response_model=APIResponse[CandidateResponse])
async def create_candidate(
    request: Request,
    cand_in: CandidateCreate,
    current_user: User = Depends(require_permissions(PermissionCode.CANDIDATE_CREATE.value)),
    db: AsyncSession = Depends(get_db)
):
    service = CandidateService(db)
    cand = await service.create_candidate(request, cand_in, current_user)
    return APIResponse(
        success=True,
        message="Candidate registered for election.",
        data=serialize_candidate(cand)
    )


@router.get("/{cand_id}", response_model=APIResponse[CandidateResponse])
async def get_candidate(
    cand_id: str,
    current_user: User = Depends(require_permissions(PermissionCode.CANDIDATE_VIEW.value)),
    db: AsyncSession = Depends(get_db)
):
    service = CandidateService(db)
    cand = await service.get_candidate(cand_id)
    return APIResponse(data=serialize_candidate(cand))


@router.put("/{cand_id}", response_model=APIResponse[CandidateResponse])
async def update_candidate(
    request: Request,
    cand_id: str,
    cand_in: CandidateUpdate,
    current_user: User = Depends(require_permissions(PermissionCode.CANDIDATE_UPDATE.value)),
    db: AsyncSession = Depends(get_db)
):
    service = CandidateService(db)
    cand = await service.update_candidate(request, cand_id, cand_in, current_user)
    return APIResponse(
        success=True,
        message="Candidate profile updated.",
        data=serialize_candidate(cand)
    )


@router.post("/{cand_id}/status", response_model=APIResponse[CandidateResponse])
async def update_candidate_status(
    request: Request,
    cand_id: str,
    status_in: CandidateStatusUpdateRequest,
    current_user: User = Depends(require_permissions(PermissionCode.CANDIDATE_APPROVE.value)),
    db: AsyncSession = Depends(get_db)
):
    service = CandidateService(db)
    cand = await service.update_candidate_status(request, cand_id, status_in, current_user)
    return APIResponse(
        success=True,
        message=f"Candidate status changed to {status_in.status.value}.",
        data=serialize_candidate(cand)
    )
