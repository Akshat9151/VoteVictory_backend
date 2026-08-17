from typing import Any, Dict, List
from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import require_permissions
from app.core.permissions import PermissionCode
from app.models.notification import NotificationTemplate
from app.models.user import User
from app.schemas.common import APIResponse
from app.schemas.notification import (
    CampaignCreate,
    CampaignResponse,
    DeliveryReportResponse,
    SendMessageRequest,
    TemplateCreate,
    TemplateResponse,
)
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notification Engine"])


@router.post("/send", response_model=APIResponse[Dict[str, Any]])
async def send_direct_message(
    send_in: SendMessageRequest,
    current_user: User = Depends(require_permissions(PermissionCode.NOTIFICATION_SEND.value)),
    db: AsyncSession = Depends(get_db)
):
    service = NotificationService(db)
    result = await service.send_direct_message(send_in, current_user)
    return APIResponse(
        success=result.get("success", True),
        message="Direct message dispatched.",
        data=result
    )


@router.post("/campaigns", response_model=APIResponse[CampaignResponse])
async def create_and_launch_campaign(
    campaign_in: CampaignCreate,
    current_user: User = Depends(require_permissions(PermissionCode.NOTIFICATION_SEND.value)),
    db: AsyncSession = Depends(get_db)
):
    service = NotificationService(db)
    campaign = await service.create_and_dispatch_campaign(campaign_in, current_user)
    return APIResponse(
        success=True,
        message=f"Campaign launched: {campaign.sent_count} messages dispatched.",
        data=campaign
    )


@router.get("/campaigns/{campaign_id}/report", response_model=APIResponse[DeliveryReportResponse])
async def get_campaign_delivery_report(
    campaign_id: str,
    current_user: User = Depends(require_permissions(PermissionCode.NOTIFICATION_VIEW.value)),
    db: AsyncSession = Depends(get_db)
):
    service = NotificationService(db)
    report = await service.get_delivery_report(campaign_id)
    return APIResponse(data=report)


@router.post("/templates", response_model=APIResponse[TemplateResponse])
async def create_template(
    template_in: TemplateCreate,
    current_user: User = Depends(require_permissions(PermissionCode.NOTIFICATION_MANAGE.value)),
    db: AsyncSession = Depends(get_db)
):
    service = NotificationService(db)
    template = await service.create_template(template_in, current_user)
    return APIResponse(
        success=True,
        message="Notification template registered.",
        data=TemplateResponse.model_validate(template)
    )


@router.get("/templates", response_model=APIResponse[List[TemplateResponse]])
async def list_templates(
    current_user: User = Depends(require_permissions(PermissionCode.NOTIFICATION_VIEW.value)),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(NotificationTemplate)
    if not current_user.is_superuser:
        stmt = stmt.where(
            (NotificationTemplate.organization_id == current_user.organization_id) | (NotificationTemplate.organization_id == None)
        )
    templates = (await db.execute(stmt)).scalars().all()
    items = [TemplateResponse.model_validate(t) for t in templates]
    return APIResponse(data=items)
