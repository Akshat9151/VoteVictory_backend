from typing import List, Optional

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import check_broadcast_rate_limit, get_current_user, get_optional_current_user, require_roles
from app.models.organization import Organization
from app.models.user import User
from app.schemas.broadcast import BroadcastPayload, BroadcastResponse, DeliveryLogResponse
from app.services.broadcast_service import BroadcastService

router = APIRouter(prefix="/broadcast", tags=["Broadcast"])


async def get_default_org_id(db: AsyncSession) -> str:
    from sqlalchemy import select
    org = (await db.execute(select(Organization).limit(1))).scalars().first()
    return org.id if org else "default_org"


@router.get("/delivery-logs", response_model=List[DeliveryLogResponse])
async def get_delivery_logs(
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve message delivery audit history."""
    org_id = current_user.organization_id if current_user else await get_default_org_id(db)
    service = BroadcastService(db)
    return await service.get_delivery_logs(organization_id=org_id)


@router.post("/send", response_model=BroadcastResponse, dependencies=[Depends(check_broadcast_rate_limit), Depends(require_roles(["superadmin", "admin"]))])
async def send_broadcast(
    request: Request,
    payload: BroadcastPayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Dispatch WhatsApp/SMS campaign message to voters across selected wards.
    Enqueues async delivery via Celery worker.
    """
    service = BroadcastService(db)
    client_ip = request.client.host if request.client else None
    return await service.send_broadcast(
        payload=payload,
        organization_id=current_user.organization_id,
        user=current_user,
        ip_address=client_ip
    )
