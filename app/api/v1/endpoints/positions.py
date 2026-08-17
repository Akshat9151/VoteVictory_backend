from typing import List
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import require_permissions
from app.core.permissions import PermissionCode
from app.models.user import User
from app.schemas.common import APIResponse
from app.schemas.position import PositionCreate, PositionResponse, PositionUpdate
from app.services.position_service import PositionService

router = APIRouter(prefix="/positions", tags=["Position Management"])


@router.get("/election/{election_id}", response_model=APIResponse[List[PositionResponse]])
async def list_positions(
    election_id: str,
    current_user: User = Depends(require_permissions(PermissionCode.ELECTION_VIEW.value)),
    db: AsyncSession = Depends(get_db)
):
    service = PositionService(db)
    positions = await service.list_positions(election_id)
    items = [PositionResponse.model_validate(p) for p in positions]
    return APIResponse(data=items)


@router.post("/", response_model=APIResponse[PositionResponse])
async def create_position(
    request: Request,
    pos_in: PositionCreate,
    current_user: User = Depends(require_permissions(PermissionCode.POSITION_MANAGE.value)),
    db: AsyncSession = Depends(get_db)
):
    service = PositionService(db)
    pos = await service.create_position(request, pos_in, current_user)
    return APIResponse(
        success=True,
        message="Election position added.",
        data=PositionResponse.model_validate(pos)
    )


@router.put("/{pos_id}", response_model=APIResponse[PositionResponse])
async def update_position(
    request: Request,
    pos_id: str,
    pos_in: PositionUpdate,
    current_user: User = Depends(require_permissions(PermissionCode.POSITION_MANAGE.value)),
    db: AsyncSession = Depends(get_db)
):
    service = PositionService(db)
    pos = await service.update_position(request, pos_id, pos_in, current_user)
    return APIResponse(
        success=True,
        message="Position updated.",
        data=PositionResponse.model_validate(pos)
    )
