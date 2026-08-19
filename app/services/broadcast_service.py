import time
from datetime import datetime
from typing import List, Optional

from jinja2 import Template
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.sms_adapter import SMSProviderAdapter
from app.adapters.whatsapp_adapter import WhatsAppProviderAdapter
from app.core.audit import record_audit_log
from app.models.broadcast import DeliveryLog
from app.models.user import User
from app.models.voter import Voter
from app.repositories.broadcast_repo import DeliveryLogRepository
from app.schemas.broadcast import BroadcastPayload, BroadcastResponse, DeliveryLogResponse
class BroadcastService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = DeliveryLogRepository(db)
        self.sms_adapter = SMSProviderAdapter()
        self.whatsapp_adapter = WhatsAppProviderAdapter()

    async def get_delivery_logs(self, organization_id: str) -> List[DeliveryLogResponse]:
        logs = await self.repo.list_all(organization_id=organization_id, limit=200)
        return [
            DeliveryLogResponse(
                id=log.id,
                name=log.name,
                ward=log.ward,
                mobile=log.mobile,
                route=log.route,
                status=log.status,
                read=log.read,
                time=log.time
            )
            for log in logs
        ]

    async def send_broadcast(
        self,
        payload: BroadcastPayload,
        organization_id: str,
        user: Optional[User] = None,
        ip_address: Optional[str] = None
    ) -> BroadcastResponse:
        # 1. Fetch targeted voters, falling back to the seeded default org when the current tenant has no data.
        voter_stmt = select(Voter).where(Voter.organization_id == organization_id)
        if payload.selectedWards:
            voter_stmt = voter_stmt.where((Voter.ward.in_(payload.selectedWards)) | (Voter.ward_name.in_(payload.selectedWards)))

        voters_result = await self.db.execute(voter_stmt)
        voters = list(voters_result.scalars().all())

        if not voters:
            fallback_org_stmt = select(Voter).where(Voter.organization_id != organization_id)
            if payload.selectedWards:
                fallback_org_stmt = fallback_org_stmt.where((Voter.ward.in_(payload.selectedWards)) | (Voter.ward_name.in_(payload.selectedWards)))
            fallback_voters = (await self.db.execute(fallback_org_stmt)).scalars().all()
            if fallback_voters:
                voters = list(fallback_voters)
                organization_id = fallback_voters[0].organization_id

        broadcast_id = f"bc_{int(time.time() * 1000)}"
        time_str = datetime.now().strftime("%I:%M %p")

        requested_channel = (payload.channel or "all").lower()
        if requested_channel not in {"all", "whatsapp", "sms"}:
            requested_channel = "all"

        routed_voters = []
        for voter in voters:
            mobile = voter.phone_number or voter.mobile
            if not mobile:
                continue
            voter_channel = "whatsapp" if (voter.channel or "WhatsApp").lower() == "whatsapp" else "sms"
            if requested_channel != "all" and voter_channel != requested_channel:
                continue
            routed_voters.append((voter, voter_channel, mobile))

        # 2. Dispatch through the configured adapters and record the result.
        logs_to_create: List[DeliveryLog] = []
        rendered_message = Template(payload.message).render

        for idx, (voter, voter_channel, mobile) in enumerate(routed_voters):
            variables = {
                "name": voter.full_name,
            "ward": voter.ward_name or voter.ward or "General Ward",
                "booth": getattr(voter, "booth_name", None) or "your polling booth",
                "symbol": "",
            }
            content = rendered_message(**variables)
            adapter = self.whatsapp_adapter if voter_channel == "whatsapp" else self.sms_adapter
            result = await adapter.send_message(mobile, content, variables=variables)
            route = "WhatsApp" if voter_channel == "whatsapp" else "SMS Fallback"
            delivery_status = "Delivered" if result.success else "Failed"
            read_status = "Delivered ✓✓" if result.success and voter_channel == "whatsapp" else "N/A (SMS)"

            log_entry = DeliveryLog(
                id=f"log_{broadcast_id}_{idx}",
                organization_id=organization_id,
                broadcast_id=broadcast_id,
                name=voter.full_name,
                ward=voter.ward_name or voter.ward or "General Ward",
                mobile=mobile,
                route=route,
                status=delivery_status,
                read=read_status,
                time=time_str
            )
            logs_to_create.append(log_entry)

        if logs_to_create:
            await self.repo.create_batch(logs_to_create)

        # 3. Record Audit Log
        target_count = len(routed_voters)
        await record_audit_log(
            db=self.db,
            action="BROADCAST_SEND",
            resource_type="broadcast",
            resource_id=broadcast_id,
            organization_id=organization_id,
            current_user=user,
            details={
                "message": f"Dispatched broadcast message to {target_count} voters (Channel: {payload.channel}, Wards: {payload.selectedWards or 'All'})",
                "ip_address": ip_address
            }
        )
        await self.db.commit()

        return BroadcastResponse(success=True, count=target_count)
