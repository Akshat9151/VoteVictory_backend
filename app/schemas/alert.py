from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.alert import AlertSeverity, OperationalAlertType


class OperationalAlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    election_id: Optional[str] = None
    alert_type: OperationalAlertType
    severity: AlertSeverity
    title: str
    message: str
    metadata_json: Optional[str] = None
    is_resolved: bool
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    created_at: datetime


class OperationalAlertResolveRequest(BaseModel):
    resolution_notes: Optional[str] = None


class OperationalAlertStatsOut(BaseModel):
    total_alerts: int
    unresolved_alerts: int
    critical_alerts: int
    high_alerts: int
