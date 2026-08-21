import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class ActivityStatus(str, enum.Enum):
    SUBMITTED = "Submitted"
    VERIFIED = "Verified"
    FLAGGED = "Flagged"


class AttendanceStatus(str, enum.Enum):
    PRESENT = "Present"
    ON_DUTY = "On-Duty"
    LEAVE = "Leave"
    ABSENT = "Absent"


class FieldActivityLog(Base):
    __tablename__ = "field_activity_logs"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    volunteer_id = Column(String(64), ForeignKey("volunteer_profiles.id", ondelete="CASCADE"), nullable=True)
    volunteer_name = Column(String(150), nullable=False)
    title = Column(String(255), nullable=True)
    submitted_by = Column(String(64), nullable=True, index=True)
    submitted_by_role = Column(String(30), nullable=False, default="VOLUNTEER", index=True)
    ward = Column(String(100), nullable=True)
    booth_no = Column(String(50), nullable=True)
    activity_type = Column(String(100), nullable=False)
    location = Column(String(255), nullable=False)
    date_time = Column(String(100), nullable=True)
    description = Column(Text, nullable=False)
    photo_url = Column(String(500), nullable=True)
    voters_contacted = Column(Integer, default=0)
    slips_distributed = Column(Integer, default=0)
    status = Column(Enum(ActivityStatus), default=ActivityStatus.SUBMITTED, nullable=False, index=True)
    reviewed_by = Column(String(64), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    volunteer = relationship("VolunteerProfile")


class VolunteerAttendanceRecord(Base):
    __tablename__ = "volunteer_attendance_records"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    volunteer_id = Column(String(64), ForeignKey("volunteer_profiles.id", ondelete="CASCADE"), nullable=True)
    volunteer_name = Column(String(150), nullable=False)
    ward = Column(String(100), nullable=True)
    date = Column(String(50), nullable=False)
    check_in_time = Column(String(50), nullable=False)
    check_out_time = Column(String(50), nullable=True)
    location = Column(String(255), nullable=False)
    status = Column(Enum(AttendanceStatus), default=AttendanceStatus.PRESENT, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    volunteer = relationship("VolunteerProfile")
