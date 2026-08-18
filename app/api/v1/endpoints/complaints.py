from typing import List, Optional
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import get_current_user, get_optional_current_user, require_roles
from app.models.organization import Organization
from app.models.user import User
from app.schemas.complaint import ComplaintCreate, ComplaintResponse, ComplaintStatusUpdate
from app.services.complaint_service import ComplaintService

router = APIRouter(prefix="/complaints", tags=["Complaints & Grievances"])


async def get_default_org_id(db: AsyncSession) -> str:
    from sqlalchemy import select
    org = (await db.execute(select(Organization).limit(1))).scalars().first()
    return org.id if org else "default_org"


@router.get("", response_model=List[ComplaintResponse])
async def get_complaints(
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve voter grievance complaints."""
    org_id = current_user.organization_id if current_user else await get_default_org_id(db)
    service = ComplaintService(db)
    return await service.get_complaints(organization_id=org_id)


@router.post("", response_model=ComplaintResponse, dependencies=[Depends(require_roles(["superadmin", "admin", "volunteer"]))])
async def add_complaint(
    request: Request,
    complaint: ComplaintCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Submit a new voter complaint or civic issue."""
    service = ComplaintService(db)
    client_ip = request.client.host if request.client else None
    return await service.add_complaint(
        data=complaint,
        organization_id=current_user.organization_id,
        user=current_user,
        ip_address=client_ip
    )


@router.patch("/{id}/status", response_model=ComplaintResponse, dependencies=[Depends(require_roles(["superadmin", "admin"]))])
async def update_complaint_status(
    id: str,
    status_update: ComplaintStatusUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update complaint status (Open -> In Progress -> Resolved) with audit logging."""
    service = ComplaintService(db)
    client_ip = request.client.host if request.client else None
    return await service.update_status(
        id=id,
        data=status_update,
        organization_id=current_user.organization_id,
        user=current_user,
        ip_address=client_ip
    )
