from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import require_permissions
from app.core.permissions import PermissionCode
from app.models.user import User
from app.schemas.audit import AuditLogFilterParams, AuditLogResponse, SecurityEventResponse
from app.schemas.common import APIResponse, PaginatedResponse
from app.services.audit_service import AuditService

router = APIRouter(prefix="/audit", tags=["Audit & Security Logs"])


@router.get("/logs", response_model=APIResponse[PaginatedResponse[AuditLogResponse]])
async def list_audit_logs(
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    actor_user_id: Optional[str] = None,
    is_success: Optional[bool] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    org_id: Optional[str] = None,
    current_user: User = Depends(require_permissions(PermissionCode.AUDIT_VIEW.value)),
    db: AsyncSession = Depends(get_db)
):
    service = AuditService(db)
    filters = AuditLogFilterParams(
        action=action,
        resource_type=resource_type,
        actor_user_id=actor_user_id,
        is_success=is_success
    )
    logs, pagination = await service.list_audit_logs(
        current_user=current_user,
        filters=filters,
        org_id=org_id,
        page=page,
        page_size=page_size
    )
    items = [AuditLogResponse.model_validate(l) for l in logs]
    return APIResponse(data=PaginatedResponse(items=items, pagination=pagination))


@router.get("/security-events", response_model=APIResponse[List[SecurityEventResponse]])
async def list_security_events(
    limit: int = Query(50, ge=1, le=100),
    org_id: Optional[str] = None,
    current_user: User = Depends(require_permissions(PermissionCode.SECURITY_VIEW.value)),
    db: AsyncSession = Depends(get_db)
):
    service = AuditService(db)
    events = await service.list_security_events(current_user, org_id, limit)
    items = [SecurityEventResponse.model_validate(e) for e in events]
    return APIResponse(data=items)
