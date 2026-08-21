from datetime import datetime
from typing import Optional, Union

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.activity import ActivityStatus, AttendanceStatus


class ActivityStatusUpdate(BaseModel):
    status: Union[ActivityStatus, str]

    @field_validator("status", mode="before")
    @classmethod
    def parse_status(cls, v):
        if isinstance(v, str):
            clean = v.strip().upper()
            mapping = {
                "APPROVED": ActivityStatus.VERIFIED,
                "VERIFIED": ActivityStatus.VERIFIED,
                "REJECTED": ActivityStatus.FLAGGED,
                "FLAGGED": ActivityStatus.FLAGGED,
                "SUBMITTED": ActivityStatus.SUBMITTED,
                "PENDING": ActivityStatus.SUBMITTED,
            }
            if clean in mapping:
                return mapping[clean]
        return v


class FieldActivityCreate(BaseModel):
    title: Optional[str] = None
    volunteer_id: Optional[str] = None
    volunteer_name: Optional[str] = "Field Volunteer"
    ward: Optional[str] = None
    booth_no: Optional[str] = None
    activity_type: str
    location: str
    date_time: Optional[str] = None
    description: str
    photo_url: Optional[str] = None
    voters_contacted: Optional[int] = 0
    slips_distributed: Optional[int] = 0


class FieldActivityResponse(BaseModel):
    id: str
    volunteer_id: Optional[str] = None
    volunteer_name: str
    title: Optional[str] = None
    submitted_by: Optional[str] = None
    submitted_by_role: str
    ward: Optional[str] = None
    booth_no: Optional[str] = None
    activity_type: str
    location: str
    date_time: Optional[str] = None
    description: str
    photo_url: Optional[str] = None
    voters_contacted: int
    slips_distributed: int
    status: Union[ActivityStatus, str]
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AttendanceCheckInRequest(BaseModel):
    volunteer_id: Optional[str] = None
    volunteer_name: str
    ward: Optional[str] = None
    location: str


class AttendanceResponse(BaseModel):
    id: str
    volunteer_id: Optional[str] = None
    volunteer_name: str
    ward: Optional[str] = None
    date: str
    check_in_time: str
    check_out_time: Optional[str] = None
    location: str
    status: AttendanceStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
