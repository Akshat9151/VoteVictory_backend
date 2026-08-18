from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog, SecurityEvent
from app.repositories.base import BaseRepository


class AuditRepository(BaseRepository[AuditLog]):
    def __init__(self, db: AsyncSession):
        super().__init__(AuditLog, db)

    async def log_audit(self, audit_entry: AuditLog) -> AuditLog:
        self.db.add(audit_entry)
        await self.db.flush()
        return audit_entry

    async def log_security_event(self, event: SecurityEvent) -> SecurityEvent:
        self.db.add(event)
        await self.db.flush()
        return event

    async def get_recent_security_events(self, org_id: Optional[str] = None, limit: int = 10) -> List[SecurityEvent]:
        stmt = select(SecurityEvent)
        if org_id:
            stmt = stmt.where(SecurityEvent.organization_id == org_id)
        stmt = stmt.order_by(SecurityEvent.created_at.desc()).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_recent_audit_logs(self, org_id: Optional[str] = None, limit: int = 10) -> List[AuditLog]:
        stmt = select(AuditLog)
        if org_id:
            stmt = stmt.where(AuditLog.organization_id == org_id)
        stmt = stmt.order_by(AuditLog.created_at.desc()).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
