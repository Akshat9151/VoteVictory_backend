from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permissions
from app.core.permissions import PermissionCode
from app.models.user import User
from app.models.volunteer import VolunteerStatus
from app.schemas.common import APIResponse, PaginatedResponse
from app.schemas.volunteer import (
    VolunteerAssignmentCreate,
    VolunteerAssignmentResponse,
    VolunteerCreate,
    VolunteerLeaderboardEntry,
    VolunteerPerformanceOut,
    VolunteerProfileOut,
    VolunteerStatusUpdate,
    VolunteerTargetCreate,
    VolunteerTargetOut,
    VolunteerTaskCreate,
    VolunteerTaskOut,
    VolunteerUpdate,
)
from app.services.volunteer_service import VolunteerService

router = APIRouter(prefix="/volunteers", tags=["Volunteer Operations & Management"])


@router.post("", response_model=APIResponse[VolunteerProfileOut])
async def create_volunteer(
    request: Request,
    volunteer_in: VolunteerCreate,
    current_user: User = Depends(require_permissions(PermissionCode.VOLUNTEER_MANAGE.value)),
    db: AsyncSession = Depends(get_db),
):
    service = VolunteerService(db)
    profile = await service.create_volunteer(request, volunteer_in, current_user)
    return APIResponse(
        success=True,
        message="Volunteer successfully registered and profile initialized.",
        data=profile,
    )


@router.get("", response_model=APIResponse[PaginatedResponse[VolunteerProfileOut]])
async def list_volunteers(
    election_id: Optional[str] = None,
    constituency_id: Optional[str] = None,
    booth_id: Optional[str] = None,
    area_id: Optional[str] = None,
    status: Optional[VolunteerStatus] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(require_permissions(PermissionCode.VOLUNTEER_VIEW.value)),
    db: AsyncSession = Depends(get_db),
):
    service = VolunteerService(db)
    skip = (page - 1) * page_size
    items, total = await service.list_volunteers(
        organization_id=current_user.organization_id,
        election_id=election_id,
        constituency_id=constituency_id,
        booth_id=booth_id,
        area_id=area_id,
        status=status,
        search=search,
        skip=skip,
        limit=page_size,
    )
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1
    return APIResponse(
        data=PaginatedResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
    )


@router.get("/leaderboard", response_model=APIResponse[List[VolunteerLeaderboardEntry]])
async def get_volunteer_leaderboard(
    election_id: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_permissions(PermissionCode.VOLUNTEER_VIEW.value)),
    db: AsyncSession = Depends(get_db),
):
    service = VolunteerService(db)
    leaderboard = await service.get_leaderboard(
        organization_id=current_user.organization_id,
        election_id=election_id,
        limit=limit,
    )
    return APIResponse(data=leaderboard)


@router.get("/{profile_id}", response_model=APIResponse[VolunteerProfileOut])
async def get_volunteer(
    profile_id: str,
    current_user: User = Depends(require_permissions(PermissionCode.VOLUNTEER_VIEW.value)),
    db: AsyncSession = Depends(get_db),
):
    service = VolunteerService(db)
    profile = await service.get_volunteer_profile(profile_id)
    return APIResponse(data=profile)


@router.patch("/{profile_id}", response_model=APIResponse[VolunteerProfileOut])
async def update_volunteer(
    request: Request,
    profile_id: str,
    update_in: VolunteerUpdate,
    current_user: User = Depends(require_permissions(PermissionCode.VOLUNTEER_MANAGE.value)),
    db: AsyncSession = Depends(get_db),
):
    service = VolunteerService(db)
    updated = await service.update_volunteer(request, profile_id, update_in, current_user)
    return APIResponse(
        success=True,
        message="Volunteer profile updated.",
        data=updated,
    )


@router.post("/{profile_id}/targets", response_model=APIResponse[VolunteerTargetOut])
async def set_volunteer_target(
    request: Request,
    profile_id: str,
    target_in: VolunteerTargetCreate,
    current_user: User = Depends(require_permissions(PermissionCode.VOLUNTEER_MANAGE.value)),
    db: AsyncSession = Depends(get_db),
):
    service = VolunteerService(db)
    target = await service.set_volunteer_target(request, profile_id, target_in, current_user)
    return APIResponse(
        success=True,
        message="Volunteer target quotas updated.",
        data=target,
    )


@router.get("/{profile_id}/performance", response_model=APIResponse[VolunteerPerformanceOut])
async def get_volunteer_performance(
    profile_id: str,
    current_user: User = Depends(require_permissions(PermissionCode.VOLUNTEER_VIEW.value)),
    db: AsyncSession = Depends(get_db),
):
    service = VolunteerService(db)
    perf = await service.get_performance(profile_id)
    return APIResponse(data=perf)


@router.post("/tasks", response_model=APIResponse[VolunteerTaskOut])
async def create_volunteer_task(
    request: Request,
    task_in: VolunteerTaskCreate,
    current_user: User = Depends(require_permissions(PermissionCode.VOLUNTEER_MANAGE.value)),
    db: AsyncSession = Depends(get_db),
):
    service = VolunteerService(db)
    task = await service.create_task(request, task_in, current_user)
    return APIResponse(
        success=True,
        message="Task assigned to volunteer.",
        data=task,
    )


@router.get("/tasks/list", response_model=APIResponse[List[VolunteerTaskOut]])
async def list_volunteer_tasks(
    volunteer_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = VolunteerService(db)
    tasks = await service.list_tasks(
        volunteer_id=volunteer_id,
        organization_id=current_user.organization_id,
    )
    return APIResponse(data=tasks)


# Legacy Polling Station Assignments
@router.get("/election/{election_id}", response_model=APIResponse[List[VolunteerAssignmentResponse]])
async def list_assignments(
    election_id: str,
    polling_station_id: Optional[str] = None,
    current_user: User = Depends(require_permissions(PermissionCode.VOLUNTEER_VIEW.value)),
    db: AsyncSession = Depends(get_db),
):
    service = VolunteerService(db)
    items = await service.list_assignments(election_id, polling_station_id)
    return APIResponse(data=items)


@router.post("/assign", response_model=APIResponse[VolunteerAssignmentResponse])
async def assign_volunteer(
    request: Request,
    assignment_in: VolunteerAssignmentCreate,
    current_user: User = Depends(require_permissions(PermissionCode.VOLUNTEER_ASSIGN.value)),
    db: AsyncSession = Depends(get_db),
):
    service = VolunteerService(db)
    assignment = await service.assign_volunteer(request, assignment_in, current_user)
    return APIResponse(
        success=True,
        message="Volunteer assigned to polling station.",
        data=VolunteerAssignmentResponse.model_validate(assignment),
    )


@router.put("/assignments/{assignment_id}", response_model=APIResponse[VolunteerAssignmentResponse])
@router.patch("/assignments/{assignment_id}", response_model=APIResponse[VolunteerAssignmentResponse])
async def update_assignment(
    request: Request,
    assignment_id: str,
    update_in: VolunteerStatusUpdate,
    current_user: User = Depends(require_permissions(PermissionCode.VOLUNTEER_ASSIGN.value)),
    db: AsyncSession = Depends(get_db),
):
    """Update volunteer polling station assignment status or details."""
    service = VolunteerService(db)
    assignment = await service.update_assignment(request, assignment_id, update_in, current_user)
    return APIResponse(
        success=True,
        message="Volunteer assignment updated.",
        data=VolunteerAssignmentResponse.model_validate(assignment),
    )

