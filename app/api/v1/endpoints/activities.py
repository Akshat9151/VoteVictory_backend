from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.activity import ActivityStatus, AttendanceStatus, FieldActivityLog, VolunteerAttendanceRecord
from app.schemas.activity import (
    AttendanceCheckInRequest,
    AttendanceResponse,
    FieldActivityCreate,
    FieldActivityResponse,
)

router = APIRouter(tags=["Field Activities & Attendance"])


# Field Activities (Section 7.7)
@router.get("/field-activities", response_model=List[FieldActivityResponse])
async def list_field_activities(
    ward: Optional[str] = Query(None),
    activity_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List real-time ground field activities with photo evidence."""
    stmt = select(FieldActivityLog)
    if ward:
        stmt = stmt.where(FieldActivityLog.ward == ward)
    if activity_type:
        stmt = stmt.where(FieldActivityLog.activity_type == activity_type)
    stmt = stmt.order_by(desc(FieldActivityLog.created_at))
    
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/field-activities", response_model=FieldActivityResponse, status_code=status.HTTP_201_CREATED)
async def submit_field_activity(
    activity_in: FieldActivityCreate,
    db: AsyncSession = Depends(get_db),
):
    """Submit ground field activity report with photos, reach count and location."""
    activity = FieldActivityLog(
        volunteer_id=activity_in.volunteer_id,
        volunteer_name=activity_in.volunteer_name,
        ward=activity_in.ward,
        booth_no=activity_in.booth_no,
        activity_type=activity_in.activity_type,
        location=activity_in.location,
        date_time=datetime.now().strftime("%d %b %Y, %I:%M %p"),
        description=activity_in.description,
        photo_url=activity_in.photo_url,
        voters_contacted=activity_in.voters_contacted or 0,
        slips_distributed=activity_in.slips_distributed or 0,
        status=ActivityStatus.SUBMITTED,
    )
    db.add(activity)
    await db.commit()
    await db.refresh(activity)
    return activity


# Volunteer Attendance (Section 7.7)
@router.get("/attendance", response_model=List[AttendanceResponse])
async def list_attendance(
    date_filter: Optional[str] = Query(None, alias="date"),
    db: AsyncSession = Depends(get_db),
):
    """Fetch volunteer daily attendance and field check-in logs."""
    stmt = select(VolunteerAttendanceRecord)
    if date_filter:
        stmt = stmt.where(VolunteerAttendanceRecord.date == date_filter)
    stmt = stmt.order_by(desc(VolunteerAttendanceRecord.created_at))
    
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/attendance/check-in", response_model=AttendanceResponse, status_code=status.HTTP_201_CREATED)
async def record_check_in(
    checkin_in: AttendanceCheckInRequest,
    db: AsyncSession = Depends(get_db),
):
    """Record 1-click volunteer daily check-in with GPS/booth location."""
    now = datetime.now()
    att = VolunteerAttendanceRecord(
        volunteer_id=checkin_in.volunteer_id,
        volunteer_name=checkin_in.volunteer_name,
        ward=checkin_in.ward or "Ward 02",
        date=now.strftime("%d %b %Y"),
        check_in_time=now.strftime("%I:%M %p"),
        location=checkin_in.location,
        status=AttendanceStatus.PRESENT,
    )
    db.add(att)
    await db.commit()
    await db.refresh(att)
    return att
