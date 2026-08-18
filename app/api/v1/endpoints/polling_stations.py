from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_permissions
from app.core.permissions import PermissionCode
from app.models.user import User
from app.schemas.common import APIResponse, PaginatedResponse
from app.schemas.polling_station import (
    PollingStationCreate,
    PollingStationResponse,
    PollingStationUpdate,
)
from app.services.station_service import PollingStationService

router = APIRouter(prefix="/polling-stations", tags=["Polling Stations"])


@router.get("/election/{election_id}", response_model=APIResponse[PaginatedResponse[PollingStationResponse]])
async def list_polling_stations(
    election_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
    current_user: User = Depends(require_permissions(PermissionCode.STATION_VIEW.value)),
    db: AsyncSession = Depends(get_db)
):
    service = PollingStationService(db)
    stations, pagination = await service.list_stations(election_id, page, page_size, search)
    items = []
    for s in stations:
        details = await service.get_station_details(s.id)
        items.append(details)
    return APIResponse(data=PaginatedResponse(items=items, pagination=pagination))


@router.post("/", response_model=APIResponse[PollingStationResponse])
async def create_polling_station(
    request: Request,
    station_in: PollingStationCreate,
    current_user: User = Depends(require_permissions(PermissionCode.STATION_MANAGE.value)),
    db: AsyncSession = Depends(get_db)
):
    service = PollingStationService(db)
    station = await service.create_station(request, station_in, current_user)
    details = await service.get_station_details(station.id)
    return APIResponse(
        success=True,
        message="Polling station configured.",
        data=details
    )


@router.get("/{station_id}", response_model=APIResponse[PollingStationResponse])
async def get_polling_station(
    station_id: str,
    current_user: User = Depends(require_permissions(PermissionCode.STATION_VIEW.value)),
    db: AsyncSession = Depends(get_db)
):
    service = PollingStationService(db)
    details = await service.get_station_details(station_id)
    return APIResponse(data=details)


@router.put("/{station_id}", response_model=APIResponse[PollingStationResponse])
async def update_polling_station(
    request: Request,
    station_id: str,
    station_in: PollingStationUpdate,
    current_user: User = Depends(require_permissions(PermissionCode.STATION_MANAGE.value)),
    db: AsyncSession = Depends(get_db)
):
    service = PollingStationService(db)
    station = await service.update_station(request, station_id, station_in, current_user)
    details = await service.get_station_details(station.id)
    return APIResponse(
        success=True,
        message="Polling station details updated.",
        data=details
    )
