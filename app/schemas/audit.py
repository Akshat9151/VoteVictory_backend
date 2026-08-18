from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.models.audit import SecuritySeverity


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: Optional[str] = None
    actor_user_id: Optional[str] = None
    actor_email: Optional[str] = None
    actor_role: Optional[str] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    ip_address: Optional[str] = None
    request_id: Optional[str] = None
    prev_state_json: Optional[str] = None
    new_state_json: Optional[str] = None
    is_success: bool
    error_message: Optional[str] = None
    created_at: datetime


class SecurityEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: Optional[str] = None
    user_id: Optional[str] = None
    event_type: str
    severity: SecuritySeverity
    details_json: Optional[str] = None
    ip_address: Optional[str] = None
    request_id: Optional[str] = None
    created_at: datetime


class AuditLogFilter(BaseModel):
    action: Optional[str] = None
    resource_type: Optional[str] = None
    actor_user_id: Optional[str] = None
    is_success: Optional[bool] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


AuditLogFilterParams = AuditLogFilter


class SecurityEventFilter(BaseModel):
    event_type: Optional[str] = None
    severity: Optional[SecuritySeverity] = None
    user_id: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
