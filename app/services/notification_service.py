import json
from datetime import datetime, timezone
from typing import Any, Dict

from jinja2 import Template
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.instagram_adapter import InstagramProviderAdapter
from app.adapters.sms_adapter import SMSProviderAdapter
from app.adapters.whatsapp_adapter import WhatsAppProviderAdapter
from app.core.exceptions import AppException, ResourceNotFoundException
from app.models.notification import (
    CampaignStatus,
    DeliveryStatus,
    NotificationCampaign,
    NotificationChannel,
    NotificationRecipient,
    NotificationTemplate,
)
from app.models.user import User
from app.models.voter import Voter, VoterStatus
from app.repositories.notification_repo import NotificationRepository
from app.schemas.notification import (
    CampaignCreate,
    CampaignResponse,
    DeliveryReportItem,
    DeliveryReportResponse,
    SendMessageRequest,
    TemplateCreate,
)


class NotificationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.notif_repo = NotificationRepository(db)
        self.sms_adapter = SMSProviderAdapter()
        self.whatsapp_adapter = WhatsAppProviderAdapter()
        self.instagram_adapter = InstagramProviderAdapter()

    def get_adapter(self, channel: NotificationChannel):
        if channel == NotificationChannel.SMS:
            return self.sms_adapter
        elif channel == NotificationChannel.WHATSAPP:
            return self.whatsapp_adapter
        elif channel == NotificationChannel.INSTAGRAM:
            return self.instagram_adapter
        else:
            return self.sms_adapter

    async def create_template(self, template_in: TemplateCreate, current_user: User) -> NotificationTemplate:
        template = NotificationTemplate(
            organization_id=template_in.organization_id or current_user.organization_id,
            name=template_in.name.strip(),
            code=template_in.code.strip().upper(),
            channel=template_in.channel,
            template_type=template_in.template_type,
            external_template_id=template_in.external_template_id,
            content_template=template_in.content_template,
            variables_schema_json=template_in.variables_schema_json,
            is_approved=True
        )
        self.db.add(template)
        await self.db.flush()
        return template

    async def send_direct_message(self, request_in: SendMessageRequest, current_user: User) -> Dict[str, Any]:
        content = request_in.message_text
        if request_in.template_id:
            tpl = await self.db.get(NotificationTemplate, request_in.template_id)
            if tpl:
                jinja_tpl = Template(tpl.content_template)
                content = jinja_tpl.render(**request_in.variables)

        if not content:
            raise AppException(code="EMPTY_NOTIFICATION_BODY", message="Notification message text or template must be provided.")

        adapter = self.get_adapter(request_in.channel)
        result = await adapter.send_message(
            recipient_address=request_in.recipient_address,
            content=content,
            template_id=request_in.template_id,
            variables=request_in.variables
        )
        return {
            "success": result.success,
            "provider_message_id": result.provider_message_id,
            "status": result.status,
            "error_message": result.error_message
        }

    async def create_and_dispatch_campaign(self, campaign_in: CampaignCreate, current_user: User) -> CampaignResponse:
        tpl = await self.db.get(NotificationTemplate, campaign_in.template_id)
        if not tpl:
            raise ResourceNotFoundException("NotificationTemplate", campaign_in.template_id)

        org_id = current_user.organization_id

        # 1. Resolve Target Audience
        voter_stmt = select(Voter).where(Voter.organization_id == org_id)
        if campaign_in.election_id:
            voter_stmt = voter_stmt.where(Voter.election_id == campaign_in.election_id)

        if campaign_in.target_audience_type == "NOT_VOTED":
            voter_stmt = voter_stmt.where(Voter.has_voted == False)
        elif campaign_in.target_audience_type == "ELIGIBLE":
            voter_stmt = voter_stmt.where(Voter.status.in_([VoterStatus.ELIGIBLE, VoterStatus.VERIFIED, VoterStatus.REGISTERED]))

        voters = (await self.db.execute(voter_stmt)).scalars().all()

        campaign = NotificationCampaign(
            organization_id=org_id,
            election_id=campaign_in.election_id,
            template_id=tpl.id,
            name=campaign_in.name.strip(),
            channel=campaign_in.channel,
            target_audience_type=campaign_in.target_audience_type,
            scheduled_at=campaign_in.scheduled_at,
            status=CampaignStatus.PROCESSING,
            total_recipients=len(voters),
            created_by=current_user.id
        )
        self.db.add(campaign)
        await self.db.flush()

        adapter = self.get_adapter(campaign.channel)
        jinja_tpl = Template(tpl.content_template)

        sent_count = 0
        failed_count = 0

        # Dispatch batch
        for v in voters:
            phone_or_handle = v.phone_number or "0000000000"
            vars_dict = {
                "name": v.full_name,
                "first_name": v.first_name,
                "ward": v.ward_name or "General Ward",
                "epic": v.voter_id_number,
                "date": datetime.now(timezone.utc).strftime("%d %b %Y")
            }
            rendered_text = jinja_tpl.render(**vars_dict)

            res = await adapter.send_message(
                recipient_address=phone_or_handle,
                content=rendered_text,
                template_id=tpl.external_template_id,
                variables=vars_dict
            )

            rec_status = DeliveryStatus.SENT if res.success else DeliveryStatus.FAILED
            if res.success:
                sent_count += 1
            else:
                failed_count += 1

            recipient = NotificationRecipient(
                campaign_id=campaign.id,
                voter_id=v.id,
                recipient_address=phone_or_handle,
                recipient_name=v.full_name,
                personalized_data_json=json.dumps(vars_dict),
                status=rec_status,
                provider_message_id=res.provider_message_id,
                error_message=res.error_message,
                sent_at=datetime.now(timezone.utc) if res.success else None
            )
            self.db.add(recipient)

        campaign.sent_count = sent_count
        campaign.failed_count = failed_count
        campaign.status = CampaignStatus.COMPLETED
        await self.db.flush()

        return CampaignResponse(
            id=campaign.id,
            organization_id=campaign.organization_id,
            election_id=campaign.election_id,
            template_id=campaign.template_id,
            name=campaign.name,
            channel=campaign.channel,
            target_audience_type=campaign.target_audience_type,
            status=campaign.status,
            total_recipients=campaign.total_recipients,
            sent_count=campaign.sent_count,
            delivered_count=campaign.delivered_count,
            failed_count=campaign.failed_count,
            scheduled_at=campaign.scheduled_at,
            created_at=campaign.created_at
        )

    async def get_delivery_report(self, campaign_id: str) -> DeliveryReportResponse:
        campaign = await self.notif_repo.get_campaign_with_recipients(campaign_id)
        if not campaign:
            raise ResourceNotFoundException("NotificationCampaign", campaign_id)

        items = [
            DeliveryReportItem(
                recipient_name=r.recipient_name,
                recipient_address=r.recipient_address,
                channel=campaign.channel.value,
                status=r.status,
                sent_at=r.sent_at,
                delivered_at=r.delivered_at,
                error_message=r.error_message
            )
            for r in campaign.recipients
        ]

        return DeliveryReportResponse(
            campaign_id=campaign.id,
            total_recipients=campaign.total_recipients,
            sent_count=campaign.sent_count,
            delivered_count=campaign.delivered_count,
            failed_count=campaign.failed_count,
            deliveries=items
        )
