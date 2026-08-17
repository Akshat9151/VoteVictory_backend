from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class VolunteerAssignmentCreate(BaseModel):
    user_id: str
    election_id: str
    polling_station_id: str
    shift_start: Optional[datetime] = None
    shift_end: Optional[datetime] = None
    task_role: str = "VERIFICATION_OFFICER"
    notes: Optional[str] = None


class VolunteerStatusUpdate(BaseModel):
    is_active: bool
    task_role: Optional[str] = None
    notes: Optional[str] = None


class VolunteerAssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    election_id: str
    polling_station_id: str
    assigned_by: Optional[str] = None
    shift_start: Optional[datetime] = None
    shift_end: Optional[datetime] = None
    task_role: str
    is_active: bool
    notes: Optional[str] = None
    volunteer_name: Optional[str] = None
    volunteer_email: Optional[str] = None
    volunteer_phone: Optional[str] = None
    station_name: Optional[str] = None
    created_at: datetime
