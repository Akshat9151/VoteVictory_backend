from typing import List, Optional
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_permissions
from app.core.permissions import PermissionCode
from app.models.notification import NotificationChannel
from app.models.user import User
from app.schemas.common import APIResponse
from app.schemas.notification import (
    TemplateCreate,
    TemplateResponse,
    TemplateUpdate,
    TemplateVariablePreviewRequest,
    TemplateVariablePreviewResponse,
)
from app.services.template_service import TemplateService

router = APIRouter(prefix="/templates", tags=["Content & Template Management"])


@router.post("", response_model=APIResponse[TemplateResponse])
async def create_template(
    request: Request,
    template_in: TemplateCreate,
    current_user: User = Depends(require_permissions(PermissionCode.TEMPLATE_MANAGE.value)),
    db: AsyncSession = Depends(get_db),
):
    service = TemplateService(db)
    template = await service.create_template(request, template_in, current_user)
    return APIResponse(success=True, message="Template created.", data=template)


@router.get("", response_model=APIResponse[List[TemplateResponse]])
async def list_templates(
    channel: Optional[NotificationChannel] = None,
    current_user: User = Depends(require_permissions(PermissionCode.NOTIFICATION_VIEW.value)),
    db: AsyncSession = Depends(get_db),
):
    service = TemplateService(db)
    templates = await service.list_templates(current_user.organization_id, channel)
    return APIResponse(data=templates)


@router.patch("/{template_id}", response_model=APIResponse[TemplateResponse])
async def update_template(
    request: Request,
    template_id: str,
    update_in: TemplateUpdate,
    current_user: User = Depends(require_permissions(PermissionCode.TEMPLATE_MANAGE.value)),
    db: AsyncSession = Depends(get_db),
):
    service = TemplateService(db)
    updated = await service.update_template(request, template_id, update_in, current_user)
    return APIResponse(success=True, message="Template updated.", data=updated)


@router.post("/preview", response_model=APIResponse[TemplateVariablePreviewResponse])
async def preview_template(
    preview_in: TemplateVariablePreviewRequest,
    current_user: User = Depends(require_permissions(PermissionCode.NOTIFICATION_VIEW.value)),
    db: AsyncSession = Depends(get_db),
):
    service = TemplateService(db)
    preview = await service.preview_template(preview_in)
    return APIResponse(data=preview)
