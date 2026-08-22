from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_roles
from app.models.user import User
from app.models.activity import ActivityStatus, AttendanceStatus, FieldActivityLog, VolunteerAttendanceRecord
from app.schemas.activity import (
    ActivityStatusUpdate,
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
    status_filter: Optional[str] = Query(None, alias="status"),
    mine: bool = Query(False),
    current_user: User = Depends(require_roles(["superadmin", "admin", "volunteer"])),
    db: AsyncSession = Depends(get_db),
):
    """List real-time ground field activities with photo evidence."""
    stmt = select(FieldActivityLog)
    if ward:
        stmt = stmt.where(FieldActivityLog.ward == ward)
    if activity_type:
        stmt = stmt.where(FieldActivityLog.activity_type == activity_type)
    if status_filter and status_filter != "all":
        stmt = stmt.where(FieldActivityLog.status == status_filter)
    if mine:
        stmt = stmt.where(FieldActivityLog.submitted_by == current_user.id)
    elif _is_volunteer(current_user):
        stmt = stmt.where(FieldActivityLog.submitted_by == current_user.id)
    elif _is_admin(current_user) and not _is_super_admin(current_user):
        stmt = stmt.where(FieldActivityLog.submitted_by_role == "VOLUNTEER")
    stmt = stmt.order_by(desc(FieldActivityLog.created_at))

    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/field-activities", response_model=FieldActivityResponse, status_code=status.HTTP_201_CREATED)
@router.post("/field-activities/submit", response_model=FieldActivityResponse, status_code=status.HTTP_201_CREATED)
async def submit_field_activity(
    activity_in: FieldActivityCreate,
    current_user: User = Depends(require_roles(["superadmin", "admin", "volunteer"])),
    db: AsyncSession = Depends(get_db),
):
    """Submit ground field activity report with photos, reach count and location."""
    activity = FieldActivityLog(
        volunteer_id=activity_in.volunteer_id if _is_volunteer(current_user) else None,
        volunteer_name=activity_in.volunteer_name or f"{current_user.first_name or ''} {current_user.last_name or ''}".strip() or "Field Volunteer",
        title=activity_in.title or activity_in.activity_type,
        submitted_by=current_user.id,
        submitted_by_role=_role_code(current_user),
        ward=activity_in.ward,
        booth_no=activity_in.booth_no,
        activity_type=activity_in.activity_type,
        location=activity_in.location,
        date_time=activity_in.date_time or datetime.now().strftime("%d %b %Y, %I:%M %p"),
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


@router.put("/field-activities/{id}/status", response_model=FieldActivityResponse)
@router.patch("/field-activities/{id}/status", response_model=FieldActivityResponse)
async def update_field_activity_status(
    id: str,
    status_in: ActivityStatusUpdate,
    current_user: User = Depends(require_roles(["superadmin", "admin", "volunteer"])),
    db: AsyncSession = Depends(get_db),
):
    """Update status after enforcing submitter-role review rules."""
    stmt = select(FieldActivityLog).where(FieldActivityLog.id == id)
    result = await db.execute(stmt)
    activity = result.scalars().first()
    if not activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Field activity '{id}' not found",
        )

    if not _can_review(current_user, activity):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot review this field activity.")

    activity.status = status_in.status
    activity.reviewed_by = current_user.id
    activity.reviewed_at = datetime.utcnow()
    if activity.status != ActivityStatus.FLAGGED:
        activity.rejection_reason = None
    await db.commit()
    await db.refresh(activity)
    return activity


@router.put("/field-activities/{id}/approve", response_model=FieldActivityResponse)
async def approve_field_activity(
    id: str,
    current_user: User = Depends(require_roles(["superadmin", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    return await _review_field_activity(id, ActivityStatus.VERIFIED, None, current_user, db)


@router.put("/field-activities/{id}/reject", response_model=FieldActivityResponse)
async def reject_field_activity(
    id: str,
    reason: Optional[str] = Query(None),
    current_user: User = Depends(require_roles(["superadmin", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    return await _review_field_activity(id, ActivityStatus.FLAGGED, reason, current_user, db)


async def _review_field_activity(
    activity_id: str,
    target_status: ActivityStatus,
    rejection_reason: Optional[str],
    current_user: User,
    db: AsyncSession,
) -> FieldActivityLog:
    activity = (await db.execute(select(FieldActivityLog).where(FieldActivityLog.id == activity_id))).scalars().first()
    if not activity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Field activity '{activity_id}' not found")
    if not _can_review(current_user, activity):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot review this field activity.")
    activity.status = target_status
    activity.reviewed_by = current_user.id
    activity.reviewed_at = datetime.utcnow()
    activity.rejection_reason = rejection_reason if target_status == ActivityStatus.FLAGGED else None

    # Create notification for the activity submitter
    if activity.user_id:
        try:
            from app.models.app_notification import AppNotification
            status_label = "Approved" if target_status == ActivityStatus.VERIFIED else "Flagged / Rejected"
            db.add(AppNotification(
                user_id=activity.user_id,
                notification_type="activity-approved",
                title=f"Field Activity {status_label}",
                message=f"Your field report '{activity.title or 'Activity'}' was marked as {status_label}.",
                link="/field-activities",
                is_read=False
            ))
            await db.flush()
        except Exception:
            pass

    await db.commit()
    await db.refresh(activity)
    return activity


def _is_volunteer(current_user: User) -> bool:
    return _role_code(current_user) == "VOLUNTEER"


def _role_code(current_user: User) -> str:
    if getattr(current_user, "is_superuser", False):
        return "SUPER_ADMIN"
    for user_role in getattr(current_user, "roles", []) or []:
        role = str(getattr(getattr(user_role, "role", None), "code", "") or "").upper()
        if role in {"SUPER_ADMIN", "ADMIN", "VOLUNTEER"}:
            return role
    return str(getattr(current_user, "role", "VOLUNTEER") or "VOLUNTEER").upper().replace(" ", "_")


def _is_super_admin(current_user: User) -> bool:
    return _role_code(current_user) == "SUPER_ADMIN"


def _is_admin(current_user: User) -> bool:
    return _role_code(current_user) == "ADMIN"


def _can_review(current_user: User, activity: FieldActivityLog) -> bool:
    if _is_super_admin(current_user):
        return True
    return _is_admin(current_user) and activity.submitted_by_role == "VOLUNTEER"


# Volunteer Attendance (Section 7.7)
@router.get("/attendance", response_model=List[AttendanceResponse])
async def list_attendance(
    date_filter: Optional[str] = Query(None, alias="date"),
    current_user: User = Depends(require_roles(["superadmin", "admin", "volunteer"])),
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
    current_user: User = Depends(require_roles(["superadmin", "admin", "volunteer"])),
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
