from typing import List, Optional

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_permissions
from app.core.permissions import PermissionCode
from app.models.banner import BannerStatus
from app.models.user import User
from app.schemas.banner import BannerCreate, BannerOut, BannerUpdate
from app.schemas.common import APIResponse
from app.services.banner_service import BannerService

router = APIRouter(prefix="/banners", tags=["Content & Banner Management"])


@router.post("", response_model=APIResponse[BannerOut])
async def create_banner(
    request: Request,
    banner_in: BannerCreate,
    current_user: User = Depends(require_permissions(PermissionCode.BANNER_MANAGE.value)),
    db: AsyncSession = Depends(get_db),
):
    service = BannerService(db)
    banner = await service.create_banner(request, banner_in, current_user)
    return APIResponse(success=True, message="Banner created.", data=banner)


@router.get("", response_model=APIResponse[List[BannerOut]])
async def list_banners(
    election_id: Optional[str] = None,
    status: Optional[BannerStatus] = None,
    current_user: User = Depends(require_permissions(PermissionCode.NOTIFICATION_VIEW.value)),
    db: AsyncSession = Depends(get_db),
):
    service = BannerService(db)
    banners = await service.list_banners(current_user.organization_id, election_id, status)
    return APIResponse(data=banners)


@router.patch("/{banner_id}", response_model=APIResponse[BannerOut])
async def update_banner(
    request: Request,
    banner_id: str,
    update_in: BannerUpdate,
    current_user: User = Depends(require_permissions(PermissionCode.BANNER_MANAGE.value)),
    db: AsyncSession = Depends(get_db),
):
    service = BannerService(db)
    updated = await service.update_banner(request, banner_id, update_in, current_user)
    return APIResponse(success=True, message="Banner updated.", data=updated)
