import enum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class VolunteerStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"
    DELETED = "DELETED"


class TaskPriority(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"


class TaskStatus(str, enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    OVERDUE = "OVERDUE"
    CANCELLED = "CANCELLED"


class ActivityType(str, enum.Enum):
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    SUBMISSION = "SUBMISSION"
    TASK_UPDATE = "TASK_UPDATE"
    TARGET_ACHIEVED = "TARGET_ACHIEVED"
    PROFILE_UPDATE = "PROFILE_UPDATE"
    SYNC = "SYNC"


class VolunteerProfile(BaseModel):
    __tablename__ = "volunteer_profiles"

    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)

    volunteer_code = Column(String(50), unique=True, nullable=False, index=True) # e.g. VOL-1002
    profile_photo_url = Column(String(512), nullable=True)
    supervisor_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # Assignments
    election_id = Column(String(36), ForeignKey("elections.id", ondelete="SET NULL"), nullable=True, index=True)
    constituency_id = Column(String(36), ForeignKey("constituencies.id", ondelete="SET NULL"), nullable=True, index=True)
    ward_id = Column(String(36), nullable=True, index=True)
    booth_id = Column(String(36), nullable=True, index=True)
    area_id = Column(String(36), nullable=True, index=True)
    polling_station_id = Column(String(36), ForeignKey("polling_stations.id", ondelete="SET NULL"), nullable=True, index=True)

    # Targets
    daily_target = Column(Integer, default=200, nullable=False)
    weekly_target = Column(Integer, default=1200, nullable=False)
    monthly_target = Column(Integer, default=5000, nullable=False)

    # Performance
    daily_collection = Column(Integer, default=0, nullable=False)
    weekly_collection = Column(Integer, default=0, nullable=False)
    monthly_collection = Column(Integer, default=0, nullable=False)
    total_submissions = Column(Integer, default=0, nullable=False)
    approved_count = Column(Integer, default=0, nullable=False)
    rejected_count = Column(Integer, default=0, nullable=False)
    duplicate_count = Column(Integer, default=0, nullable=False)

    # Status & Activity
    status = Column(Enum(VolunteerStatus), default=VolunteerStatus.ACTIVE, nullable=False, index=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    last_submission_at = Column(DateTime(timezone=True), nullable=True)
    last_activity_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="volunteer_profile")
    supervisor = relationship("User", foreign_keys=[supervisor_id])
    organization = relationship("Organization")
    election = relationship("Election")
    constituency = relationship("Constituency")
    polling_station = relationship("PollingStation")
    targets = relationship("VolunteerTarget", back_populates="volunteer_profile", cascade="all, delete-orphan")
    tasks = relationship("VolunteerTask", back_populates="volunteer_profile", cascade="all, delete-orphan")
    activities = relationship("VolunteerActivity", back_populates="volunteer_profile", cascade="all, delete-orphan")


class VolunteerTarget(BaseModel):
    __tablename__ = "volunteer_targets"

    volunteer_profile_id = Column(String(36), ForeignKey("volunteer_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    election_id = Column(String(36), ForeignKey("elections.id", ondelete="SET NULL"), nullable=True, index=True)
    area_id = Column(String(36), nullable=True, index=True)

    daily_target = Column(Integer, default=200, nullable=False)
    weekly_target = Column(Integer, default=1200, nullable=False)
    monthly_target = Column(Integer, default=5000, nullable=False)

    target_start_date = Column(DateTime(timezone=True), nullable=True)
    target_end_date = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)

    volunteer_profile = relationship("VolunteerProfile", back_populates="targets")


class VolunteerTask(BaseModel):
    __tablename__ = "volunteer_tasks"

    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    volunteer_profile_id = Column(String(36), ForeignKey("volunteer_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    assigned_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    election_id = Column(String(36), ForeignKey("elections.id", ondelete="SET NULL"), nullable=True, index=True)
    area_id = Column(String(36), nullable=True, index=True)
    booth_id = Column(String(36), nullable=True, index=True)

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    target_count = Column(Integer, default=100, nullable=False)
    completed_count = Column(Integer, default=0, nullable=False)
    deadline = Column(DateTime(timezone=True), nullable=True)
    priority = Column(Enum(TaskPriority), default=TaskPriority.MEDIUM, nullable=False)
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING, nullable=False, index=True)

    volunteer_profile = relationship("VolunteerProfile", back_populates="tasks")


class VolunteerActivity(BaseModel):
    __tablename__ = "volunteer_activities"

    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    volunteer_profile_id = Column(String(36), ForeignKey("volunteer_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    activity_type = Column(Enum(ActivityType), nullable=False, index=True)
    description = Column(String(500), nullable=False)
    metadata_json = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)
    device_info = Column(String(255), nullable=True)

    volunteer_profile = relationship("VolunteerProfile", back_populates="activities")
