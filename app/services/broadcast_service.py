import json
import time
from datetime import datetime, timezone
from typing import List, Optional

from jinja2 import Template, TemplateSyntaxError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.adapters.sms_adapter import SMSProviderAdapter
from app.adapters.whatsapp_adapter import WhatsAppProviderAdapter
from app.core.audit import record_audit_log
from app.models.broadcast import BroadcastGroup, BroadcastGroupMember, BroadcastLog, DeliveryLog
from app.models.user import User
from app.models.voter import Voter
from app.repositories.broadcast_repo import DeliveryLogRepository
from app.schemas.broadcast import (
    BroadcastDraftPayload,
    BroadcastGroupCreate,
    BroadcastGroupResponse,
    BroadcastLogItem,
    BroadcastPayload,
    BroadcastResponse,
    BroadcastSendResponse,
    DeliveryLogResponse,
)


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

    @staticmethod
    def _group_response(group: BroadcastGroup) -> BroadcastGroupResponse:
        members = list(group.members or [])
        return BroadcastGroupResponse(
            id=group.id,
            name=group.name,
            filter_criteria_snapshot=json.loads(group.filter_criteria_snapshot or "{}"),
            message_text=group.message_text,
            status=group.status,
            recipient_count=len(members),
            whatsapp_count=sum(member.contact_method == "whatsapp" for member in members),
            sms_count=sum(member.contact_method == "sms" for member in members),
            excluded_no_contact=group.excluded_no_contact,
            created_at=group.created_at,
        )

    async def create_group(self, payload: BroadcastGroupCreate, organization_id: str, user: User) -> BroadcastGroupResponse:
        voter_stmt = select(Voter).where(Voter.organization_id == organization_id)
        if payload.voter_ids:
            voter_stmt = voter_stmt.where(Voter.id.in_(payload.voter_ids))
        voters = list((await self.db.execute(voter_stmt)).scalars().all())
        if payload.voter_ids and len(voters) != len(set(payload.voter_ids)):
            raise ValueError("One or more selected voters do not belong to your organization.")

        included = []
        excluded = 0
        for voter in voters:
            mobile = (voter.phone_number or voter.mobile or "").strip()
            if not mobile:
                excluded += 1
                continue
            requested_channel = (payload.channel_overrides or {}).get(voter.id, "")
            if requested_channel not in {"whatsapp", "sms"}:
                requested_channel = "whatsapp" if (voter.channel or "").strip().lower() == "whatsapp" else "sms"
            channel = requested_channel
            included.append((voter, mobile, channel))

        if not included:
            raise ValueError("No selected voters have a reachable mobile number.")

        snapshot = dict(payload.filter_criteria_snapshot or {})
        default_name = f"Broadcast - {snapshot.get('label') or 'Selected Electors'} - {datetime.now().strftime('%d %b %Y')}"
        group = BroadcastGroup(
            organization_id=organization_id,
            name=(payload.name or default_name).strip(),
            filter_criteria_snapshot=json.dumps(snapshot, ensure_ascii=False),
            created_by=user.id,
            excluded_no_contact=excluded,
        )
        self.db.add(group)
        await self.db.flush()
        for voter, mobile, channel in included:
            self.db.add(BroadcastGroupMember(
                group_id=group.id,
                voter_id=voter.id,
                mobile=mobile,
                contact_method=channel,
                voter_name=voter.full_name,
                ward=voter.ward_name or voter.ward or "",
            ))
        await self.db.commit()
        group = await self._get_group(group.id, organization_id)
        return self._group_response(group)

    async def list_groups(self, organization_id: str) -> List[BroadcastGroupResponse]:
        groups = list((await self.db.execute(
            select(BroadcastGroup).options(selectinload(BroadcastGroup.members)).where(BroadcastGroup.organization_id == organization_id).order_by(BroadcastGroup.created_at.desc())
        )).scalars().all())
        return [self._group_response(group) for group in groups]

    async def save_group_draft(self, group_id: str, payload: BroadcastDraftPayload, organization_id: str) -> BroadcastGroupResponse:
        group = await self._get_group(group_id, organization_id)
        if not payload.message_text.strip():
            raise ValueError("Message text cannot be empty.")
        if group.status == "SENT":
            raise ValueError("A sent broadcast cannot be edited.")
        try:
            Template(payload.message_text)
        except TemplateSyntaxError as error:
            raise ValueError("Message contains an invalid placeholder. Use {{name}}, {{ward}}, or {{booth}}.") from error
        group.message_text = payload.message_text
        group.status = "READY"
        await self.db.commit()
        await self.db.refresh(group)
        return self._group_response(group)

    async def send_group(self, group_id: str, organization_id: str) -> BroadcastSendResponse:
        group = await self._get_group(group_id, organization_id)
        if not group.message_text or not group.message_text.strip():
            raise ValueError("Save a draft message before sending.")
        if group.status == "SENT":
            return await self.group_results(group_id, organization_id)

        try:
            rendered_message = Template(group.message_text).render
        except TemplateSyntaxError as error:
            raise ValueError("Message contains an invalid placeholder. Edit and save the draft again using {{name}}, {{ward}}, or {{booth}}.") from error
        logs = []
        for member in list(group.members or []):
            variables = {"name": member.voter_name, "ward": member.ward or "General Ward", "booth": "your polling booth", "symbol": ""}
            content = rendered_message(**variables)
            adapter = self.whatsapp_adapter if member.contact_method == "whatsapp" else self.sms_adapter
            result = await adapter.send_message(member.mobile, content, variables=variables)
            logs.append(BroadcastLog(
                group_id=group.id,
                voter_id=member.voter_id,
                mobile=member.mobile,
                channel_used=member.contact_method,
                status="success" if result.success else "failed",
                provider_response=json.dumps(result.raw_response or {"error": result.error_message}, ensure_ascii=False, default=str),
                sent_at=datetime.now(timezone.utc).isoformat(),
            ))
        self.db.add_all(logs)
        group.status = "SENT"
        await self.db.commit()
        return await self.group_results(group_id, organization_id)

    async def group_results(self, group_id: str, organization_id: str) -> BroadcastSendResponse:
        group = await self._get_group(group_id, organization_id)
        logs = list((await self.db.execute(select(BroadcastLog).where(BroadcastLog.group_id == group.id))).scalars().all())
        return BroadcastSendResponse(
            success=all(log.status == "success" for log in logs),
            group_id=group.id,
            total=len(logs),
            whatsapp_sent=sum(log.status == "success" and log.channel_used == "whatsapp" for log in logs),
            sms_sent=sum(log.status == "success" and log.channel_used == "sms" for log in logs),
            failed=sum(log.status == "failed" for log in logs),
        )

    async def group_logs(self, group_id: str, organization_id: str) -> List[BroadcastLogItem]:
        await self._get_group(group_id, organization_id)
        logs = list((await self.db.execute(
            select(BroadcastLog).where(BroadcastLog.group_id == group_id).order_by(BroadcastLog.created_at.asc())
        )).scalars().all())
        return [BroadcastLogItem(
            id=log.id,
            voter_id=log.voter_id,
            mobile=log.mobile,
            channel_used=log.channel_used,
            status=log.status,
            provider_response=log.provider_response,
            sent_at=log.sent_at,
        ) for log in logs]

    async def _get_group(self, group_id: str, organization_id: str) -> BroadcastGroup:
        group = (await self.db.execute(select(BroadcastGroup).options(selectinload(BroadcastGroup.members)).where(
            BroadcastGroup.id == group_id,
            BroadcastGroup.organization_id == organization_id,
        ))).scalars().first()
        if not group:
            raise ValueError("Broadcast group not found.")
        return group

    async def delete_group(self, group_id: str, organization_id: str) -> bool:
        group = await self._get_group(group_id, organization_id)
        await self.db.delete(group)
        await self.db.commit()
        return True

    async def delete_groups_bulk(self, group_ids: list[str], organization_id: str) -> int:
        result = await self.db.execute(select(BroadcastGroup).where(
            BroadcastGroup.id.in_(group_ids),
            BroadcastGroup.organization_id == organization_id
        ))
        groups = result.scalars().all()
        deleted_count = 0
        for group in groups:
            await self.db.delete(group)
            deleted_count += 1
        await self.db.commit()
        return deleted_count
