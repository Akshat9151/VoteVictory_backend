from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.notification import (
    DeliveryStatus,
    NotificationCampaign,
    NotificationDelivery,
    NotificationRecipient,
    NotificationTemplate,
)
from app.repositories.base import BaseRepository


class NotificationRepository(BaseRepository[NotificationCampaign]):
    def __init__(self, db: AsyncSession):
        super().__init__(NotificationCampaign, db)

    async def get_template_by_code(self, org_id: Optional[str], code: str) -> Optional[NotificationTemplate]:
        stmt = select(NotificationTemplate).where(NotificationTemplate.code == code)
        if org_id:
            stmt = stmt.where((NotificationTemplate.organization_id == org_id) | (NotificationTemplate.organization_id == None))
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_campaign_with_recipients(self, campaign_id: str) -> Optional[NotificationCampaign]:
        stmt = (
            select(NotificationCampaign)
            .options(
                selectinload(NotificationCampaign.recipients),
                selectinload(NotificationCampaign.template)
            )
            .where(NotificationCampaign.id == campaign_id)
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_recipient_by_provider_message_id(self, provider_message_id: str) -> Optional[NotificationRecipient]:
        stmt = select(NotificationRecipient).where(NotificationRecipient.provider_message_id == provider_message_id)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def add_delivery_event(self, delivery: NotificationDelivery) -> NotificationDelivery:
        self.db.add(delivery)
        await self.db.flush()
        return delivery
