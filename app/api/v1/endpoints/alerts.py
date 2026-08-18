from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_permissions
from app.core.permissions import PermissionCode
from app.models.alert import AlertSeverity
from app.models.user import User
from app.schemas.alert import (
    OperationalAlertOut,
    OperationalAlertResolveRequest,
    OperationalAlertStatsOut,
)
from app.schemas.common import APIResponse
from app.services.alert_service import AlertService

router = APIRouter(prefix="/alerts", tags=["Operational Alerts"])


@router.get("", response_model=APIResponse[List[OperationalAlertOut]])
async def list_alerts(
    is_resolved: Optional[bool] = None,
    severity: Optional[AlertSeverity] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(require_permissions(PermissionCode.ALERT_MANAGE.value)),
    db: AsyncSession = Depends(get_db),
):
    service = AlertService(db)
    alerts = await service.list_alerts(
        organization_id=current_user.organization_id,
        is_resolved=is_resolved,
        severity=severity,
        skip=skip,
        limit=limit,
    )
    return APIResponse(data=alerts)


@router.post("/{alert_id}/resolve", response_model=APIResponse[OperationalAlertOut])
async def resolve_alert(
    request: Request,
    alert_id: str,
    resolve_in: OperationalAlertResolveRequest,
    current_user: User = Depends(require_permissions(PermissionCode.ALERT_MANAGE.value)),
    db: AsyncSession = Depends(get_db),
):
    service = AlertService(db)
    resolved = await service.resolve_alert(request, alert_id, resolve_in, current_user)
    return APIResponse(success=True, message="Alert resolved.", data=resolved)


@router.get("/stats", response_model=APIResponse[OperationalAlertStatsOut])
async def get_alert_stats(
    current_user: User = Depends(require_permissions(PermissionCode.ALERT_MANAGE.value)),
    db: AsyncSession = Depends(get_db),
):
    service = AlertService(db)
    stats = await service.get_alert_statistics(current_user.organization_id)
    return APIResponse(data=stats)
