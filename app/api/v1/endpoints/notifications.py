from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, status
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permissions
from app.core.permissions import PermissionCode
from app.models.app_notification import AppNotification
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


@router.get("/my", response_model=APIResponse[List[Dict[str, Any]]])
async def list_my_notifications(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    notifications = (await db.execute(
        select(AppNotification)
        .where(AppNotification.user_id == current_user.id)
        .order_by(AppNotification.created_at.desc())
        .limit(50)
    )).scalars().all()

    items = [
        {
            "id": item.id,
            "type": getattr(item, "notification_type", "general") or "general",
            "title": getattr(item, "title", "Notification") or "Notification",
            "message": item.message,
            "link": getattr(item, "link", None) or ("/studio" if item.related_poster_id else "/"),
            "timestamp": item.created_at.isoformat() if item.created_at else None,
            "read": item.is_read,
            "data": {"poster_id": item.related_poster_id},
        }
        for item in notifications
    ]
    return APIResponse(data=items)


@router.patch("/{notification_id}/read", response_model=APIResponse[bool])
async def mark_notification_read(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        update(AppNotification)
        .where(AppNotification.id == notification_id, AppNotification.user_id == current_user.id)
        .values(is_read=True)
    )
    await db.commit()
    return APIResponse(success=True, message="Marked as read.", data=True)


@router.post("/mark-all-read", response_model=APIResponse[bool])
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        update(AppNotification)
        .where(AppNotification.user_id == current_user.id)
        .values(is_read=True)
    )
    await db.commit()
    return APIResponse(success=True, message="All marked as read.", data=True)


@router.delete("/{notification_id}", response_model=APIResponse[bool])
async def delete_notification(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        delete(AppNotification)
        .where(AppNotification.id == notification_id, AppNotification.user_id == current_user.id)
    )
    await db.commit()
    return APIResponse(success=True, message="Notification removed.", data=True)
