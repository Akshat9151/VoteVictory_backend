from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_permissions
from app.core.permissions import PermissionCode
from app.models.user import User
from app.schemas.checkin import VoterCheckinRequest, VoterCheckinResponse
from app.schemas.common import APIResponse
from app.services.checkin_service import CheckinService

router = APIRouter(prefix="/checkin", tags=["Voter Check-in"])


@router.post("/", response_model=APIResponse[VoterCheckinResponse])
async def checkin_voter(
    request: Request,
    checkin_in: VoterCheckinRequest,
    current_user: User = Depends(require_permissions(PermissionCode.VOTER_CHECKIN.value)),
    db: AsyncSession = Depends(get_db)
):
    service = CheckinService(db)
    response = await service.checkin_voter(request, checkin_in, current_user)
    return APIResponse(
        success=True,
        message=response.message,
        data=response
    )
