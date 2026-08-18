from typing import List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog, SecurityEvent
from app.models.user import User
from app.repositories.audit_repo import AuditRepository
from app.schemas.audit import AuditLogFilterParams
from app.schemas.common import PaginationMeta


class AuditService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.audit_repo = AuditRepository(db)

    async def list_audit_logs(
        self,
        current_user: User,
        filters: AuditLogFilterParams,
        org_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 50
    ) -> Tuple[List[AuditLog], PaginationMeta]:
        stmt_filters = {}
        if not current_user.is_superuser:
            stmt_filters["organization_id"] = current_user.organization_id
        elif org_id:
            stmt_filters["organization_id"] = org_id

        if filters.action:
            stmt_filters["action"] = filters.action
        if filters.resource_type:
            stmt_filters["resource_type"] = filters.resource_type
        if filters.actor_user_id:
            stmt_filters["actor_user_id"] = filters.actor_user_id
        if filters.is_success is not None:
            stmt_filters["is_success"] = filters.is_success

        return await self.audit_repo.list_paginated(
            page=page,
            page_size=page_size,
            filters=stmt_filters,
            search_fields=["action", "actor_email", "resource_type", "resource_id"]
        )

    async def list_security_events(
        self,
        current_user: User,
        org_id: Optional[str] = None,
        limit: int = 50
    ) -> List[SecurityEvent]:
        target_org = current_user.organization_id if not current_user.is_superuser else org_id
        return await self.audit_repo.get_recent_security_events(target_org, limit)
