import json
from typing import Any, Dict, Optional

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog, SecurityEvent, SecuritySeverity
from app.models.user import User


async def record_audit_log(
    db: AsyncSession,
    request: Optional[Request] = None,
    action: str = "MUTATION",
    resource_type: str = "UNKNOWN",
    resource_id: Optional[str] = None,
    current_user: Optional[User] = None,
    organization_id: Optional[str] = None,
    prev_state: Optional[Dict[str, Any]] = None,
    new_state: Optional[Dict[str, Any]] = None,
    is_success: bool = True,
    error_message: Optional[str] = None,
    actor_id: Optional[str] = None,
    actor_name: Optional[str] = None,
    actor_role: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> AuditLog:
    """Creates an immutable audit log entry."""
    request_id = getattr(request.state, "request_id", None) if request and hasattr(request, "state") else None
    client_ip = request.client.host if request and request.client else "127.0.0.1"
    user_agent = request.headers.get("User-Agent") if request and hasattr(request, "headers") else None

    # Determine actor information
    act_id = actor_id or (current_user.id if current_user else None)
    act_email = actor_name or (current_user.email if current_user else "system")
    act_role = actor_role or (getattr(current_user, "role", None) if current_user else None)
    if not act_role and current_user and hasattr(current_user, "roles") and current_user.roles:
        act_role = current_user.roles[0].role.code if hasattr(current_user.roles[0], "role") else None

    org_id = organization_id or (current_user.organization_id if current_user else "default_org")

    payload_state = new_state or details

    audit_entry = AuditLog(
        organization_id=org_id,
        actor_user_id=act_id,
        actor_email=act_email,
        actor_role=act_role,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id else None,
        ip_address=client_ip,
        user_agent=user_agent,
        request_id=request_id,
        prev_state_json=json.dumps(prev_state) if prev_state else None,
        new_state_json=json.dumps(payload_state) if payload_state else None,
        is_success=is_success,
        error_message=error_message
    )
    db.add(audit_entry)
    await db.flush()
    return audit_entry


log_audit_event = record_audit_log


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
    request_id = getattr(request.state, "request_id", None) if request and hasattr(request, "state") else None
    client_ip = request.client.host if request and request.client else "127.0.0.1"
    user_agent = request.headers.get("User-Agent") if request and hasattr(request, "headers") else None

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
