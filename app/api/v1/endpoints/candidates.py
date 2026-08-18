from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import inspect, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_optional_current_user, require_permissions
from app.core.permissions import PermissionCode
from app.models.candidate import Candidate, CandidateStatus
from app.models.organization import Organization
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


async def get_default_org_id(db: AsyncSession) -> str:
    org = (await db.execute(select(Organization).limit(1))).scalars().first()
    return org.id if org else "default_org"


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
    c_name = c.name or c.full_name or "Candidate"
    return CandidateResponse(
        id=c.id,
        organization_id=c.organization_id,
        election_id=c.election_id or "",
        position_id=c.position_id or "",
        constituency_id=c.constituency_id,
        name=c_name,
        hindiName=c.hindiName or c_name,
        post=c.post or "Sarpanch (Gram Panchayat)",
        postType=c.postType or "sarpanch",
        constituency=c.constituency_name or "Gram Panchayat Rampur (Ward 04)",
        symbol=c.symbol or "🚜",
        symbolName=c.symbolName or "Tractor (ट्रैक्टर)",
        photo=c.photo or c.photo_url or "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=400&auto=format&fit=crop&q=80",
        slogan=c.slogan or "गांव का समग्र विकास, हर घर विश्वास और खुशहाली!",
        votersCount=c.votersCount if c.votersCount is not None else 3500,
        volunteersCount=c.volunteersCount if c.volunteersCount is not None else 24,
        manifesto=c.manifesto or "",
        full_name=c.full_name or c_name,
        candidate_id_number=c.candidate_id_number,
        party_name=c.party_name or c.symbolName,
        party_symbol_url=c.party_symbol_url or c.symbol,
        photo_url=c.photo_url or c.photo,
        phone=c.phone,
        email=c.email,
        status=c.status or CandidateStatus.APPROVED,
        display_order=c.display_order or 0,
        rejection_reason=c.rejection_reason,
        approved_by=c.approved_by,
        documents=docs,
        created_at=c.created_at,
        updated_at=c.updated_at
    )


@router.get("", response_model=List[CandidateResponse])
@router.get("/", response_model=List[CandidateResponse])
async def get_candidates(
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve all candidates registered for the campaign organization."""
    org_id = current_user.organization_id if current_user else await get_default_org_id(db)
    service = CandidateService(db)
    candidates = await service.list_org_candidates(organization_id=org_id)
    if not candidates:
        candidates = await service.list_org_candidates(organization_id=None)
    return [serialize_candidate(c) for c in candidates]


@router.post("", response_model=CandidateResponse)
@router.post("/", response_model=CandidateResponse)
async def add_candidate(
    request: Request,
    cand_in: CandidateCreate,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Add a new candidate for the campaign."""
    org_id = current_user.organization_id if current_user else await get_default_org_id(db)
    if not cand_in.election_id:
        cand_in.election_id = org_id
    service = CandidateService(db)
    cand = await service.create_candidate(request, cand_in, current_user)
    return serialize_candidate(cand)


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
