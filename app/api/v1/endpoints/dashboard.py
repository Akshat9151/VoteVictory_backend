from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permissions, require_super_admin
from app.core.permissions import PermissionCode
from app.models.user import User
from app.schemas.common import APIResponse
from app.schemas.dashboard import (
    AdminDashboardResponse,
    SuperAdminDashboardResponse,
    VolunteerDashboardResponse,
)
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["Operational Dashboard Command Center"])


@router.get("/superadmin", response_model=APIResponse[SuperAdminDashboardResponse])
async def get_super_admin_dashboard(
    election_id: Optional[str] = None,
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    service = DashboardService(db)
    data = await service.get_super_admin_dashboard(election_id=election_id)
    return APIResponse(data=data)


@router.get("/admin", response_model=APIResponse[AdminDashboardResponse])
@router.get("/admin/{election_id}", response_model=APIResponse[AdminDashboardResponse])
async def get_admin_dashboard(
    election_id: Optional[str] = None,
    current_user: User = Depends(require_permissions(PermissionCode.DASHBOARD_VIEW.value)),
    db: AsyncSession = Depends(get_db),
):
    service = DashboardService(db)
    data = await service.get_admin_dashboard(election_id=election_id, organization_id=current_user.organization_id)
    return APIResponse(data=data)


@router.get("/overview", response_model=APIResponse[AdminDashboardResponse])
async def get_dashboard_overview(
    election_id: Optional[str] = None,
    current_user: User = Depends(require_permissions(PermissionCode.DASHBOARD_VIEW.value)),
    db: AsyncSession = Depends(get_db),
):
    service = DashboardService(db)
    data = await service.get_admin_dashboard(election_id=election_id, organization_id=current_user.organization_id)
    return APIResponse(data=data)


@router.get("/volunteer", response_model=APIResponse[VolunteerDashboardResponse])
async def get_volunteer_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = DashboardService(db)
    data = await service.get_volunteer_dashboard(current_user)
    return APIResponse(data=data)
