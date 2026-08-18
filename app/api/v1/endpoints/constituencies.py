from typing import List

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_permissions
from app.core.permissions import PermissionCode
from app.models.user import User
from app.schemas.common import APIResponse
from app.schemas.constituency import ConstituencyCreate, ConstituencyResponse, ConstituencyUpdate
from app.services.constituency_service import ConstituencyService

router = APIRouter(prefix="/constituencies", tags=["Constituency Management"])


@router.get("/election/{election_id}", response_model=APIResponse[List[ConstituencyResponse]])
async def list_constituencies(
    election_id: str,
    current_user: User = Depends(require_permissions(PermissionCode.ELECTION_VIEW.value)),
    db: AsyncSession = Depends(get_db)
):
    service = ConstituencyService(db)
    items = await service.list_constituencies(election_id)
    return APIResponse(data=[ConstituencyResponse.model_validate(c) for c in items])


@router.post("/", response_model=APIResponse[ConstituencyResponse])
async def create_constituency(
    request: Request,
    con_in: ConstituencyCreate,
    current_user: User = Depends(require_permissions(PermissionCode.CONSTITUENCY_MANAGE.value)),
    db: AsyncSession = Depends(get_db)
):
    service = ConstituencyService(db)
    con = await service.create_constituency(request, con_in, current_user)
    return APIResponse(
        success=True,
        message="Constituency created.",
        data=ConstituencyResponse.model_validate(con)
    )


@router.put("/{con_id}", response_model=APIResponse[ConstituencyResponse])
async def update_constituency(
    request: Request,
    con_id: str,
    con_in: ConstituencyUpdate,
    current_user: User = Depends(require_permissions(PermissionCode.CONSTITUENCY_MANAGE.value)),
    db: AsyncSession = Depends(get_db)
):
    service = ConstituencyService(db)
    con = await service.update_constituency(request, con_id, con_in, current_user)
    return APIResponse(
        success=True,
        message="Constituency updated.",
        data=ConstituencyResponse.model_validate(con)
    )
