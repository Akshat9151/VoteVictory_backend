from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import require_permissions
from app.core.permissions import PermissionCode
from app.models.user import User
from app.schemas.analytics import TurnoutAnalyticsResponse
from app.schemas.common import APIResponse
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics & Turnout Engine"])


@router.get("/election/{election_id}/turnout", response_model=APIResponse[TurnoutAnalyticsResponse])
async def get_turnout_analytics(
    election_id: str,
    current_user: User = Depends(require_permissions(PermissionCode.DASHBOARD_VIEW.value)),
    db: AsyncSession = Depends(get_db)
):
    service = AnalyticsService(db)
    data = await service.get_election_turnout_analytics(election_id)
    return APIResponse(data=data)
