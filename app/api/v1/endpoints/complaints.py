from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_optional_current_user
from app.models.organization import Organization
from app.models.user import User
from app.schemas.common import APIResponse, PaginatedResponse, PaginationMeta
from app.schemas.complaint import ComplaintCreate, ComplaintResponse, ComplaintStatusUpdate
from app.services.complaint_service import ComplaintService

router = APIRouter(prefix="/complaints", tags=["Complaints & Grievances"])


async def get_default_org_id(db: AsyncSession) -> str:
    org = (await db.execute(select(Organization).limit(1))).scalars().first()
    return org.id if org else "default_org"


@router.get("", response_model=List[ComplaintResponse])
@router.get("/", response_model=List[ComplaintResponse])
async def get_complaints(
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve voter grievance complaints."""
    org_id = current_user.organization_id if current_user else await get_default_org_id(db)
    service = ComplaintService(db)
    return await service.get_complaints(organization_id=org_id)


@router.get("/election/{election_id}", response_model=APIResponse[PaginatedResponse[ComplaintResponse]])
async def list_election_complaints(
    election_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve grievances associated with an active election."""
    org_id = current_user.organization_id if current_user else await get_default_org_id(db)
    service = ComplaintService(db)
    items = await service.get_complaints(organization_id=org_id)
    total_items = len(items)
    pagination = PaginationMeta(
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=max(1, (total_items + page_size - 1) // page_size),
        has_next=False,
        has_prev=False,
    )
    return APIResponse(
        success=True,
        message="Complaints retrieved successfully.",
        data=PaginatedResponse(items=items, pagination=pagination, total=total_items),
    )


@router.post("", response_model=ComplaintResponse)
@router.post("/", response_model=ComplaintResponse)
async def add_complaint(
    request: Request,
    complaint: ComplaintCreate,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit a new voter complaint or civic issue."""
    org_id = current_user.organization_id if current_user else await get_default_org_id(db)
    service = ComplaintService(db)
    client_ip = request.client.host if request.client else None
    return await service.add_complaint(
        data=complaint,
        organization_id=org_id,
        user=current_user,
        ip_address=client_ip,
    )


@router.post("/election/{election_id}", response_model=APIResponse[ComplaintResponse])
async def add_election_complaint(
    election_id: str,
    request: Request,
    complaint: ComplaintCreate,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit a complaint for a specific election."""
    org_id = current_user.organization_id if current_user else await get_default_org_id(db)
    complaint.election_id = election_id
    service = ComplaintService(db)
    client_ip = request.client.host if request.client else None
    created = await service.add_complaint(
        data=complaint,
        organization_id=org_id,
        user=current_user,
        ip_address=client_ip,
    )
    return APIResponse(
        success=True,
        message="Grievance logged successfully.",
        data=created,
    )


@router.put("/{id}/status", response_model=ComplaintResponse)
@router.patch("/{id}/status", response_model=ComplaintResponse)
async def update_complaint_status(
    id: str,
    status_update: ComplaintStatusUpdate,
    request: Request,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update complaint status (Open -> In Progress -> Resolved) with audit logging."""
    org_id = current_user.organization_id if current_user else None
    service = ComplaintService(db)
    client_ip = request.client.host if request.client else None
    return await service.update_status(
        id=id,
        data=status_update,
        organization_id=org_id,
        user=current_user,
        ip_address=client_ip,
    )
