from typing import List, Optional
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_permissions
from app.core.permissions import PermissionCode
from app.models.user import User
from app.schemas.area import (
    AreaCreate,
    AreaOut,
    AreaUpdate,
    BoothCreate,
    BoothOut,
    BoothStatsOut,
    BoothUpdate,
    MapMetricsOut,
    WardCreate,
    WardOut,
    WardUpdate,
)
from app.schemas.common import APIResponse
from app.services.area_booth_service import AreaBoothService

router = APIRouter(prefix="/geography", tags=["Geographical Hierarchy & Booth Operations"])


# Wards
@router.post("/wards", response_model=APIResponse[WardOut])
async def create_ward(
    request: Request,
    ward_in: WardCreate,
    current_user: User = Depends(require_permissions(PermissionCode.CONSTITUENCY_MANAGE.value)),
    db: AsyncSession = Depends(get_db),
):
    service = AreaBoothService(db)
    ward = await service.create_ward(request, ward_in, current_user)
    return APIResponse(success=True, message="Ward created.", data=ward)


@router.get("/wards", response_model=APIResponse[List[WardOut]])
async def list_wards(
    constituency_id: Optional[str] = None,
    current_user: User = Depends(require_permissions(PermissionCode.ELECTION_VIEW.value)),
    db: AsyncSession = Depends(get_db),
):
    service = AreaBoothService(db)
    wards = await service.list_wards(current_user.organization_id, constituency_id)
    return APIResponse(data=wards)


# Booths
@router.post("/booths", response_model=APIResponse[BoothOut])
async def create_booth(
    request: Request,
    booth_in: BoothCreate,
    current_user: User = Depends(require_permissions(PermissionCode.BOOTH_MANAGE.value)),
    db: AsyncSession = Depends(get_db),
):
    service = AreaBoothService(db)
    booth = await service.create_booth(request, booth_in, current_user)
    return APIResponse(success=True, message="Booth created.", data=booth)


@router.get("/booths", response_model=APIResponse[List[BoothOut]])
async def list_booths(
    constituency_id: Optional[str] = None,
    ward_id: Optional[str] = None,
    current_user: User = Depends(require_permissions(PermissionCode.ELECTION_VIEW.value)),
    db: AsyncSession = Depends(get_db),
):
    service = AreaBoothService(db)
    booths = await service.list_booths(current_user.organization_id, constituency_id, ward_id)
    return APIResponse(data=booths)


@router.get("/booths/{booth_id}/stats", response_model=APIResponse[BoothStatsOut])
async def get_booth_stats(
    booth_id: str,
    current_user: User = Depends(require_permissions(PermissionCode.ELECTION_VIEW.value)),
    db: AsyncSession = Depends(get_db),
):
    service = AreaBoothService(db)
    stats = await service.get_booth_stats(booth_id)
    return APIResponse(data=stats)


# Areas & Map
@router.post("/areas", response_model=APIResponse[AreaOut])
async def create_area(
    request: Request,
    area_in: AreaCreate,
    current_user: User = Depends(require_permissions(PermissionCode.AREA_MANAGE.value)),
    db: AsyncSession = Depends(get_db),
):
    service = AreaBoothService(db)
    area = await service.create_area(request, area_in, current_user)
    return APIResponse(success=True, message="Area created.", data=area)


@router.get("/areas", response_model=APIResponse[List[AreaOut]])
async def list_areas(
    constituency_id: Optional[str] = None,
    booth_id: Optional[str] = None,
    current_user: User = Depends(require_permissions(PermissionCode.ELECTION_VIEW.value)),
    db: AsyncSession = Depends(get_db),
):
    service = AreaBoothService(db)
    areas = await service.list_areas(current_user.organization_id, constituency_id, booth_id)
    return APIResponse(data=areas)


@router.get("/map-metrics", response_model=APIResponse[List[MapMetricsOut]])
async def get_map_metrics(
    current_user: User = Depends(require_permissions(PermissionCode.ELECTION_VIEW.value)),
    db: AsyncSession = Depends(get_db),
):
    service = AreaBoothService(db)
    metrics = await service.get_map_metrics(current_user.organization_id)
    return APIResponse(data=metrics)
