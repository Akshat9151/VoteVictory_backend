import json
from typing import Any, Dict, Optional
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit import AuditLog, SecurityEvent, SecuritySeverity
from app.models.user import User


async def record_audit_log(
    db: AsyncSession,
    request: Request,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    current_user: Optional[User] = None,
    organization_id: Optional[str] = None,
    prev_state: Optional[Dict[str, Any]] = None,
    new_state: Optional[Dict[str, Any]] = None,
    is_success: bool = True,
    error_message: Optional[str] = None
) -> AuditLog:
    """Creates an immutable audit log entry."""
    request_id = getattr(request.state, "request_id", None)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")

    # Determine actor information
    actor_id = current_user.id if current_user else None
    actor_email = current_user.email if current_user else "anonymous"
    actor_role = None
    if current_user and current_user.roles:
        actor_role = current_user.roles[0].role.code if hasattr(current_user.roles[0], "role") else None
    
    org_id = organization_id or (current_user.organization_id if current_user else None)

    audit_entry = AuditLog(
        organization_id=org_id,
        actor_user_id=actor_id,
        actor_email=actor_email,
        actor_role=actor_role,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id else None,
        ip_address=client_ip,
        user_agent=user_agent,
        request_id=request_id,
        prev_state_json=json.dumps(prev_state) if prev_state else None,
        new_state_json=json.dumps(new_state) if new_state else None,
        is_success=is_success,
        error_message=error_message
    )
    db.add(audit_entry)
    await db.flush()
    return audit_entry


async def record_security_event(
    db: AsyncSession,
    request: Request,
    event_type: str,
    severity: SecuritySeverity = SecuritySeverity.LOW,
    user_id: Optional[str] = None,
    organization_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> SecurityEvent:
    """Emits an alertable security monitoring event."""
    request_id = getattr(request.state, "request_id", None)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")

    event = SecurityEvent(
        organization_id=organization_id,
        user_id=user_id,
        event_type=event_type,
        severity=severity,
        details_json=json.dumps(details) if details else None,
        ip_address=client_ip,
        user_agent=user_agent,
        request_id=request_id
    )
    db.add(event)
    await db.flush()
    return event
