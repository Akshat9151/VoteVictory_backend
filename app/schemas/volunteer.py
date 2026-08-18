from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.volunteer import ActivityType, TaskPriority, TaskStatus, VolunteerStatus


class VolunteerBase(BaseModel):
    name: str
    role: str
    ward: str
    phone: str
    votersAdded: int = 0
    callsMade: int = 0
    slipsDistributed: int = 0
    status: str = "Active"


class VolunteerResponse(VolunteerBase):
    id: str

    model_config = ConfigDict(from_attributes=True)


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


class VolunteerCreate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    name: Optional[str] = None
    role: Optional[str] = None
    ward: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    password: Optional[str] = None
    volunteer_code: Optional[str] = None
    profile_photo_url: Optional[str] = None
    supervisor_id: Optional[str] = None
    election_id: Optional[str] = None
    constituency_id: Optional[str] = None
    ward_id: Optional[str] = None
    booth_id: Optional[str] = None
    area_id: Optional[str] = None
    polling_station_id: Optional[str] = None
    daily_target: int = 200
    weekly_target: int = 1200
    monthly_target: int = 5000


class VolunteerUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    profile_photo_url: Optional[str] = None
    supervisor_id: Optional[str] = None
    election_id: Optional[str] = None
    constituency_id: Optional[str] = None
    ward_id: Optional[str] = None
    booth_id: Optional[str] = None
    area_id: Optional[str] = None
    polling_station_id: Optional[str] = None
    daily_target: Optional[int] = None
    weekly_target: Optional[int] = None
    monthly_target: Optional[int] = None
    status: Optional[VolunteerStatus] = None


class VolunteerProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    organization_id: str
    volunteer_code: str
    profile_photo_url: Optional[str] = None
    name: str
    email: str
    phone: Optional[str] = None
    supervisor_id: Optional[str] = None
    supervisor_name: Optional[str] = None
    election_id: Optional[str] = None
    constituency_id: Optional[str] = None
    ward_id: Optional[str] = None
    booth_id: Optional[str] = None
    area_id: Optional[str] = None
    polling_station_id: Optional[str] = None

    daily_target: int
    weekly_target: int
    monthly_target: int
    daily_collection: int
    weekly_collection: int
    monthly_collection: int
    total_submissions: int
    approved_count: int
    rejected_count: int
    duplicate_count: int

    approval_rate: float = 0.0
    rejection_rate: float = 0.0
    duplicate_rate: float = 0.0
    achievement_percentage: float = 0.0

    status: VolunteerStatus
    last_login_at: Optional[datetime] = None
    last_submission_at: Optional[datetime] = None
    last_activity_at: Optional[datetime] = None
    created_at: datetime


class VolunteerTargetCreate(BaseModel):
    daily_target: int
    weekly_target: int
    monthly_target: int
    election_id: Optional[str] = None
    area_id: Optional[str] = None
    target_start_date: Optional[datetime] = None
    target_end_date: Optional[datetime] = None
    notes: Optional[str] = None


class VolunteerTargetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    volunteer_profile_id: str
    organization_id: str
    election_id: Optional[str] = None
    area_id: Optional[str] = None
    daily_target: int
    weekly_target: int
    monthly_target: int
    target_start_date: Optional[datetime] = None
    target_end_date: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime


class VolunteerPerformanceOut(BaseModel):
    volunteer_id: str
    volunteer_name: str
    volunteer_code: str
    daily_target: int
    weekly_target: int
    monthly_target: int
    daily_collection: int
    weekly_collection: int
    monthly_collection: int
    total_submissions: int
    approved_count: int
    rejected_count: int
    duplicate_count: int
    achievement_percentage: float
    remaining_target: int
    approval_rate: float
    rejection_rate: float
    duplicate_rate: float
    performance_trend: str = "STEADY"


class VolunteerLeaderboardEntry(BaseModel):
    rank: int
    volunteer_id: str
    volunteer_name: str
    volunteer_code: str
    area_name: Optional[str] = None
    booth_number: Optional[str] = None
    collected_count: int
    approved_count: int
    achievement_percentage: float
    badge: Optional[str] = None


class VolunteerTaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    volunteer_id: str
    election_id: Optional[str] = None
    area_id: Optional[str] = None
    booth_id: Optional[str] = None
    target_count: int = 100
    deadline: Optional[datetime] = None
    priority: TaskPriority = TaskPriority.MEDIUM


class VolunteerTaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    target_count: Optional[int] = None
    completed_count: Optional[int] = None
    deadline: Optional[datetime] = None
    priority: Optional[TaskPriority] = None
    status: Optional[TaskStatus] = None


class VolunteerTaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    volunteer_profile_id: str
    assigned_by: Optional[str] = None
    election_id: Optional[str] = None
    area_id: Optional[str] = None
    booth_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    target_count: int
    completed_count: int
    deadline: Optional[datetime] = None
    priority: TaskPriority
    status: TaskStatus
    created_at: datetime


class VolunteerActivityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    volunteer_profile_id: str
    activity_type: ActivityType
    description: str
    metadata_json: Optional[str] = None
    ip_address: Optional[str] = None
    device_info: Optional[str] = None
    created_at: datetime
