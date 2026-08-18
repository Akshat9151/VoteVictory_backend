from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from app.models.activity import ActivityStatus, AttendanceStatus


class FieldActivityCreate(BaseModel):
    volunteer_id: Optional[UUID] = None
    volunteer_name: str
    ward: Optional[str] = None
    booth_no: Optional[str] = None
    activity_type: str
    location: str
    description: str
    photo_url: Optional[str] = None
    voters_contacted: Optional[int] = 0
    slips_distributed: Optional[int] = 0


class FieldActivityResponse(BaseModel):
    id: UUID
    volunteer_id: Optional[UUID] = None
    volunteer_name: str
    ward: Optional[str] = None
    booth_no: Optional[str] = None
    activity_type: str
    location: str
    description: str
    photo_url: Optional[str] = None
    voters_contacted: int
    slips_distributed: int
    status: ActivityStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AttendanceCheckInRequest(BaseModel):
    volunteer_id: Optional[UUID] = None
    volunteer_name: str
    ward: Optional[str] = None
    location: str


class AttendanceResponse(BaseModel):
    id: UUID
    volunteer_id: Optional[UUID] = None
    volunteer_name: str
    ward: Optional[str] = None
    date: str
    check_in_time: str
    check_out_time: Optional[str] = None
    location: str
    status: AttendanceStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
