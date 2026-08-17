from typing import List, Optional
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import require_permissions
from app.core.permissions import PermissionCode
from app.models.user import User
from app.schemas.common import APIResponse
from app.schemas.volunteer import (
    VolunteerAssignmentCreate,
    VolunteerAssignmentResponse,
    VolunteerStatusUpdate,
)
from app.services.volunteer_service import VolunteerService

router = APIRouter(prefix="/volunteers", tags=["Volunteer Assignments"])


@router.get("/election/{election_id}", response_model=APIResponse[List[VolunteerAssignmentResponse]])
async def list_assignments(
    election_id: str,
    polling_station_id: Optional[str] = None,
    current_user: User = Depends(require_permissions(PermissionCode.VOLUNTEER_VIEW.value)),
    db: AsyncSession = Depends(get_db)
):
    service = VolunteerService(db)
    items = await service.list_assignments(election_id, polling_station_id)
    return APIResponse(data=items)


@router.post("/assign", response_model=APIResponse[VolunteerAssignmentResponse])
async def assign_volunteer(
    request: Request,
    assignment_in: VolunteerAssignmentCreate,
    current_user: User = Depends(require_permissions(PermissionCode.VOLUNTEER_ASSIGN.value)),
    db: AsyncSession = Depends(get_db)
):
    service = VolunteerService(db)
    assignment = await service.assign_volunteer(request, assignment_in, current_user)
    return APIResponse(
        success=True,
        message="Volunteer assigned to polling station.",
        data=VolunteerAssignmentResponse.model_validate(assignment)
    )


@router.put("/assignments/{assignment_id}", response_model=APIResponse[VolunteerAssignmentResponse])
async def update_assignment_status(
    request: Request,
    assignment_id: str,
    update_in: VolunteerStatusUpdate,
    current_user: User = Depends(require_permissions(PermissionCode.VOLUNTEER_ASSIGN.value)),
    db: AsyncSession = Depends(get_db)
):
    service = VolunteerService(db)
    assignment = await service.update_status(request, assignment_id, update_in, current_user)
    return APIResponse(
        success=True,
        message="Volunteer status updated.",
        data=VolunteerAssignmentResponse.model_validate(assignment)
    )
