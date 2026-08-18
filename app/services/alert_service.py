from datetime import datetime, timezone
from typing import List, Optional

from fastapi import Request
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit_log
from app.core.exceptions import ResourceNotFoundException
from app.models.alert import AlertSeverity, OperationalAlert, OperationalAlertType
from app.models.user import User
from app.repositories.base import BaseRepository
from app.schemas.alert import (
    OperationalAlertOut,
    OperationalAlertResolveRequest,
    OperationalAlertStatsOut,
)


class AlertService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = BaseRepository(OperationalAlert, db)

    async def trigger_alert(
        self,
        organization_id: str,
        alert_type: OperationalAlertType,
        severity: AlertSeverity,
        title: str,
        message: str,
        election_id: Optional[str] = None,
        metadata_json: Optional[str] = None,
    ) -> OperationalAlert:
        alert = OperationalAlert(
            organization_id=organization_id,
            election_id=election_id,
            alert_type=alert_type,
            severity=severity,
            title=title,
            message=message,
            metadata_json=metadata_json,
            is_resolved=False,
        )
        return await self.repo.create(alert)

    async def list_alerts(
        self,
        organization_id: Optional[str] = None,
        is_resolved: Optional[bool] = None,
        severity: Optional[AlertSeverity] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[OperationalAlertOut]:
        stmt = select(OperationalAlert)
        if organization_id:
            stmt = stmt.where(OperationalAlert.organization_id == organization_id)
        if is_resolved is not None:
            stmt = stmt.where(OperationalAlert.is_resolved == is_resolved)
        if severity is not None:
            stmt = stmt.where(OperationalAlert.severity == severity)

        stmt = stmt.order_by(desc(OperationalAlert.created_at)).offset(skip).limit(limit)
        results = (await self.db.execute(stmt)).scalars().all()
        return [OperationalAlertOut.model_validate(a) for a in results]

    async def resolve_alert(
        self,
        request: Request,
        alert_id: str,
        resolve_in: OperationalAlertResolveRequest,
        current_user: User,
    ) -> OperationalAlertOut:
        alert = await self.repo.get_by_id(alert_id)
        if not alert:
            raise ResourceNotFoundException("OperationalAlert", alert_id)

        alert.is_resolved = True
        alert.resolved_by = current_user.id
        alert.resolved_at = datetime.now(timezone.utc)
        alert.resolution_notes = resolve_in.resolution_notes

        updated = await self.repo.update(alert)
        await record_audit_log(
            self.db,
            request,
            action="alert.resolve",
            resource_type="operational_alert",
            resource_id=alert.id,
            current_user=current_user,
            new_state={"is_resolved": True},
        )
        return OperationalAlertOut.model_validate(updated)

    async def get_alert_statistics(self, organization_id: Optional[str] = None) -> OperationalAlertStatsOut:
        stmt = select(OperationalAlert)
        if organization_id:
            stmt = stmt.where(OperationalAlert.organization_id == organization_id)
        results = (await self.db.execute(stmt)).scalars().all()

        total = len(results)
        unresolved = sum(1 for a in results if not a.is_resolved)
        critical = sum(1 for a in results if not a.is_resolved and a.severity == AlertSeverity.CRITICAL)
        high = sum(1 for a in results if not a.is_resolved and a.severity == AlertSeverity.HIGH)

        return OperationalAlertStatsOut(
            total_alerts=total,
            unresolved_alerts=unresolved,
            critical_alerts=critical,
            high_alerts=high,
        )
