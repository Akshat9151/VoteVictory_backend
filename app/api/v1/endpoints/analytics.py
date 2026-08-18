from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_permissions
from app.core.permissions import PermissionCode
from app.models.user import User
from app.schemas.analytics import AnalyticsChartsResponse
from app.schemas.common import APIResponse
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Operational Analytics & Charts Engine"])


@router.get("/charts", response_model=APIResponse[AnalyticsChartsResponse])
async def get_charts_analytics(
    election_id: Optional[str] = None,
    current_user: User = Depends(require_permissions(PermissionCode.DASHBOARD_VIEW.value)),
    db: AsyncSession = Depends(get_db),
):
    service = AnalyticsService(db)
    data = await service.get_charts_data(current_user.organization_id, election_id)
    return APIResponse(data=data)
