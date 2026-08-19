import uuid
from datetime import datetime, timezone
from typing import Any, List, Optional, Tuple

from fastapi import Request
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.audit import record_audit_log
from app.core.exceptions import ConflictException, ResourceNotFoundException
from app.core.security import get_password_hash
from app.models.election import Election
from app.models.organization import Organization
from app.models.polling_station import VolunteerAssignment
from app.models.user import Role, RoleCode, User, UserRole
from app.models.volunteer import (
    ActivityType,
    TaskStatus,
    VolunteerActivity,
    VolunteerProfile,
    VolunteerStatus,
    VolunteerTarget,
    VolunteerTask,
)
from app.repositories.base import BaseRepository
from app.schemas.volunteer import (
    VolunteerAssignmentCreate,
    VolunteerAssignmentResponse,
    VolunteerCreate,
    VolunteerLeaderboardEntry,
    VolunteerPerformanceOut,
    VolunteerProfileOut,
    VolunteerTargetCreate,
    VolunteerTargetOut,
    VolunteerTaskCreate,
    VolunteerTaskOut,
    VolunteerUpdate,
)


class VolunteerService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.assignment_repo = BaseRepository(VolunteerAssignment, db)
        self.profile_repo = BaseRepository(VolunteerProfile, db)
        self.target_repo = BaseRepository(VolunteerTarget, db)
        self.task_repo = BaseRepository(VolunteerTask, db)
        self.activity_repo = BaseRepository(VolunteerActivity, db)

    async def _resolve_org_id(self, current_user: User, election_id: Optional[str] = None) -> str:
        if current_user.organization_id:
            return current_user.organization_id
        if election_id:
            election = await self.db.get(Election, election_id)
            if election:
                return election.organization_id
        stmt = select(Organization).limit(1)
        org = (await self.db.execute(stmt)).scalars().first()
        return org.id if org else ""

    async def create_volunteer(
        self,
        request: Request,
        volunteer_in: VolunteerCreate,
        current_user: User,
    ) -> VolunteerProfileOut:
        org_id = await self._resolve_org_id(current_user, volunteer_in.election_id)

        # Check if email already exists
        stmt = select(User).where(User.email == volunteer_in.email)
        existing_user = (await self.db.execute(stmt)).scalar_one_or_none()
        if existing_user:
            raise ConflictException(f"User with email '{volunteer_in.email}' already exists")

        volunteer_code = volunteer_in.volunteer_code or f"VOL-{uuid.uuid4().hex[:6].upper()}"

        user = User(
            organization_id=org_id,
            email=volunteer_in.email,
            phone=volunteer_in.phone,
            password_hash=get_password_hash(volunteer_in.password),
            first_name=volunteer_in.first_name,
            last_name=volunteer_in.last_name,
            is_active=True,
            is_verified=True,
        )
        self.db.add(user)
        await self.db.flush()

        role_stmt = select(Role).where(Role.code == RoleCode.VOLUNTEER.value)
        role = (await self.db.execute(role_stmt)).scalar_one_or_none()
        if role:
            user_role = UserRole(user_id=user.id, role_id=role.id)
            self.db.add(user_role)

        profile = VolunteerProfile(
            user_id=user.id,
            organization_id=org_id,
            volunteer_code=volunteer_code,
            profile_photo_url=volunteer_in.profile_photo_url,
            supervisor_id=volunteer_in.supervisor_id,
            election_id=volunteer_in.election_id,
            constituency_id=volunteer_in.constituency_id,
            ward_id=volunteer_in.ward_id,
            booth_id=volunteer_in.booth_id,
            area_id=volunteer_in.area_id,
            polling_station_id=volunteer_in.polling_station_id,
            daily_target=volunteer_in.daily_target,
            weekly_target=volunteer_in.weekly_target,
            monthly_target=volunteer_in.monthly_target,
            status=VolunteerStatus.ACTIVE,
            last_activity_at=datetime.now(timezone.utc),
        )
        self.db.add(profile)
        await self.db.flush()

        target = VolunteerTarget(
            volunteer_profile_id=profile.id,
            organization_id=org_id,
            election_id=volunteer_in.election_id,
            area_id=volunteer_in.area_id,
            daily_target=volunteer_in.daily_target,
            weekly_target=volunteer_in.weekly_target,
            monthly_target=volunteer_in.monthly_target,
            target_start_date=datetime.now(timezone.utc),
            notes="Initial target quota allocation",
        )
        self.db.add(target)

        activity = VolunteerActivity(
            organization_id=org_id,
            volunteer_profile_id=profile.id,
            activity_type=ActivityType.PROFILE_UPDATE,
            description="Volunteer onboarded to the system",
        )
        self.db.add(activity)

        await self.db.commit()

        await record_audit_log(
            self.db,
            request,
            action="volunteer.create",
            resource_type="volunteer_profile",
            resource_id=profile.id,
            current_user=current_user,
            new_state={"volunteer_code": volunteer_code, "user_id": user.id},
        )

        return await self.get_volunteer_profile(profile.id)

    async def list_volunteers(
        self,
        organization_id: Optional[str] = None,
        election_id: Optional[str] = None,
        constituency_id: Optional[str] = None,
        booth_id: Optional[str] = None,
        area_id: Optional[str] = None,
        status: Optional[VolunteerStatus] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[VolunteerProfileOut], int]:
        stmt = (
            select(VolunteerProfile)
            .options(
                selectinload(VolunteerProfile.user),
                selectinload(VolunteerProfile.supervisor),
            )
        )
        if organization_id:
            stmt = stmt.where(VolunteerProfile.organization_id == organization_id)
        if election_id:
            stmt = stmt.where(VolunteerProfile.election_id == election_id)
        if constituency_id:
            stmt = stmt.where(VolunteerProfile.constituency_id == constituency_id)
        if booth_id:
            stmt = stmt.where(VolunteerProfile.booth_id == booth_id)
        if area_id:
            stmt = stmt.where(VolunteerProfile.area_id == area_id)
        if status:
            stmt = stmt.where(VolunteerProfile.status == status)

        if search:
            search_pattern = f"%{search}%"
            stmt = stmt.join(VolunteerProfile.user).where(
                (VolunteerProfile.volunteer_code.ilike(search_pattern))
                | (User.first_name.ilike(search_pattern))
                | (User.last_name.ilike(search_pattern))
                | (User.email.ilike(search_pattern))
                | (User.phone.ilike(search_pattern))
            )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_stmt)).scalar_one()

        stmt = stmt.order_by(desc(VolunteerProfile.created_at)).offset(skip).limit(limit)
        results = (await self.db.execute(stmt)).scalars().all()

        profiles = []
        for p in results:
            profiles.append(self._to_profile_out(p))

        return profiles, total

    async def get_volunteer_profile(self, profile_id: str) -> VolunteerProfileOut:
        stmt = (
            select(VolunteerProfile)
            .options(
                selectinload(VolunteerProfile.user),
                selectinload(VolunteerProfile.supervisor),
            )
            .where(VolunteerProfile.id == profile_id)
        )
        profile = (await self.db.execute(stmt)).scalar_one_or_none()
        if not profile:
            raise ResourceNotFoundException("VolunteerProfile", profile_id)

        return self._to_profile_out(profile)

    async def update_volunteer(
        self,
        request: Request,
        profile_id: str,
        update_in: VolunteerUpdate,
        current_user: User,
    ) -> VolunteerProfileOut:
        stmt = (
            select(VolunteerProfile)
            .options(
                selectinload(VolunteerProfile.user),
                selectinload(VolunteerProfile.supervisor),
            )
            .where(VolunteerProfile.id == profile_id)
        )
        profile = (await self.db.execute(stmt)).scalar_one_or_none()
        if not profile:
            raise ResourceNotFoundException("VolunteerProfile", profile_id)

        if profile.user:
            if update_in.first_name:
                profile.user.first_name = update_in.first_name
            if update_in.last_name:
                profile.user.last_name = update_in.last_name
            if update_in.phone:
                profile.user.phone = update_in.phone

        if update_in.profile_photo_url is not None:
            profile.profile_photo_url = update_in.profile_photo_url
        if update_in.supervisor_id is not None:
            profile.supervisor_id = update_in.supervisor_id
        if update_in.election_id is not None:
            profile.election_id = update_in.election_id
        if update_in.constituency_id is not None:
            profile.constituency_id = update_in.constituency_id
        if update_in.ward_id is not None:
            profile.ward_id = update_in.ward_id
        if update_in.booth_id is not None:
            profile.booth_id = update_in.booth_id
        if update_in.area_id is not None:
            profile.area_id = update_in.area_id
        if update_in.polling_station_id is not None:
            profile.polling_station_id = update_in.polling_station_id
        if update_in.daily_target is not None:
            profile.daily_target = update_in.daily_target
        if update_in.weekly_target is not None:
            profile.weekly_target = update_in.weekly_target
        if update_in.monthly_target is not None:
            profile.monthly_target = update_in.monthly_target
        if update_in.status is not None:
            profile.status = update_in.status

        await self.db.commit()

        await record_audit_log(
            self.db,
            request,
            action="volunteer.update",
            resource_type="volunteer_profile",
            resource_id=profile.id,
            current_user=current_user,
            new_state={"status": str(profile.status)},
        )

        return self._to_profile_out(profile)

    async def set_volunteer_target(
        self,
        request: Request,
        profile_id: str,
        target_in: VolunteerTargetCreate,
        current_user: User,
    ) -> VolunteerTargetOut:
        profile = await self.profile_repo.get_by_id(profile_id)
        if not profile:
            raise ResourceNotFoundException("VolunteerProfile", profile_id)

        org_id = await self._resolve_org_id(current_user, target_in.election_id or profile.election_id)

        profile.daily_target = target_in.daily_target
        profile.weekly_target = target_in.weekly_target
        profile.monthly_target = target_in.monthly_target

        target = VolunteerTarget(
            volunteer_profile_id=profile.id,
            organization_id=org_id,
            election_id=target_in.election_id or profile.election_id,
            area_id=target_in.area_id or profile.area_id,
            daily_target=target_in.daily_target,
            weekly_target=target_in.weekly_target,
            monthly_target=target_in.monthly_target,
            target_start_date=target_in.target_start_date or datetime.now(timezone.utc),
            target_end_date=target_in.target_end_date,
            notes=target_in.notes,
        )
        self.db.add(target)
        await self.db.commit()
        await self.db.refresh(target)

        await record_audit_log(
            self.db,
            request,
            action="volunteer.target_set",
            resource_type="volunteer_target",
            resource_id=target.id,
            current_user=current_user,
            new_state={"daily": target.daily_target, "monthly": target.monthly_target},
        )

        return VolunteerTargetOut.model_validate(target)

    async def get_performance(self, profile_id: str) -> VolunteerPerformanceOut:
        profile_out = await self.get_volunteer_profile(profile_id)
        remaining = max(0, profile_out.monthly_target - profile_out.monthly_collection)
        trend = "IMPROVING" if profile_out.achievement_percentage >= 80.0 else ("DECLINING" if profile_out.achievement_percentage < 40.0 else "STEADY")

        return VolunteerPerformanceOut(
            volunteer_id=profile_out.id,
            volunteer_name=profile_out.name,
            volunteer_code=profile_out.volunteer_code,
            daily_target=profile_out.daily_target,
            weekly_target=profile_out.weekly_target,
            monthly_target=profile_out.monthly_target,
            daily_collection=profile_out.daily_collection,
            weekly_collection=profile_out.weekly_collection,
            monthly_collection=profile_out.monthly_collection,
            total_submissions=profile_out.total_submissions,
            approved_count=profile_out.approved_count,
            rejected_count=profile_out.rejected_count,
            duplicate_count=profile_out.duplicate_count,
            achievement_percentage=profile_out.achievement_percentage,
            remaining_target=remaining,
            approval_rate=profile_out.approval_rate,
            rejection_rate=profile_out.rejection_rate,
            duplicate_rate=profile_out.duplicate_rate,
            performance_trend=trend,
        )

    async def get_leaderboard(
        self,
        organization_id: Optional[str] = None,
        election_id: Optional[str] = None,
        limit: int = 20,
    ) -> List[VolunteerLeaderboardEntry]:
        stmt = (
            select(VolunteerProfile)
            .options(selectinload(VolunteerProfile.user))
            .where(VolunteerProfile.status == VolunteerStatus.ACTIVE)
        )
        if organization_id:
            stmt = stmt.where(VolunteerProfile.organization_id == organization_id)
        if election_id:
            stmt = stmt.where(VolunteerProfile.election_id == election_id)

        stmt = stmt.order_by(desc(VolunteerProfile.total_submissions)).limit(limit)
        results = (await self.db.execute(stmt)).scalars().all()

        leaderboard = []
        for idx, p in enumerate(results, start=1):
            achieve_pct = round((p.monthly_collection / p.monthly_target * 100) if p.monthly_target > 0 else 0.0, 2)
            badge = "GOLD" if idx == 1 else ("SILVER" if idx == 2 else ("BRONZE" if idx == 3 else None))
            leaderboard.append(
                VolunteerLeaderboardEntry(
                    rank=idx,
                    volunteer_id=p.id,
                    volunteer_name=p.user.full_name if p.user else "Volunteer",
                    volunteer_code=p.volunteer_code,
                    collected_count=p.total_submissions,
                    approved_count=p.approved_count,
                    achievement_percentage=achieve_pct,
                    badge=badge,
                )
            )
        return leaderboard

    async def create_task(
        self,
        request: Request,
        task_in: VolunteerTaskCreate,
        current_user: User,
    ) -> VolunteerTaskOut:
        org_id = await self._resolve_org_id(current_user, task_in.election_id)
        task = VolunteerTask(
            organization_id=org_id,
            volunteer_profile_id=task_in.volunteer_id,
            assigned_by=current_user.id,
            election_id=task_in.election_id,
            area_id=task_in.area_id,
            booth_id=task_in.booth_id,
            title=task_in.title,
            description=task_in.description,
            target_count=task_in.target_count,
            deadline=task_in.deadline,
            priority=task_in.priority,
            status=TaskStatus.PENDING,
        )
        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)

        await record_audit_log(
            self.db,
            request,
            action="volunteer.task_create",
            resource_type="volunteer_task",
            resource_id=task.id,
            current_user=current_user,
            new_state={"title": task.title, "priority": str(task.priority)},
        )

        return VolunteerTaskOut.model_validate(task)

    async def list_tasks(
        self,
        volunteer_id: Optional[str] = None,
        organization_id: Optional[str] = None,
    ) -> List[VolunteerTaskOut]:
        stmt = select(VolunteerTask)
        if volunteer_id:
            stmt = stmt.where(VolunteerTask.volunteer_profile_id == volunteer_id)
        if organization_id:
            stmt = stmt.where(VolunteerTask.organization_id == organization_id)

        stmt = stmt.order_by(desc(VolunteerTask.created_at))
        results = (await self.db.execute(stmt)).scalars().all()
        return [VolunteerTaskOut.model_validate(t) for t in results]

    async def assign_volunteer(
        self,
        request: Request,
        assignment_in: VolunteerAssignmentCreate,
        current_user: User,
    ) -> VolunteerAssignment:
        assignment = VolunteerAssignment(
            user_id=assignment_in.user_id,
            election_id=assignment_in.election_id,
            polling_station_id=assignment_in.polling_station_id,
            assigned_by=current_user.id,
            shift_start=assignment_in.shift_start,
            shift_end=assignment_in.shift_end,
            task_role=assignment_in.task_role,
            is_active=True,
            notes=assignment_in.notes,
        )
        assignment = await self.assignment_repo.create(assignment)

        await record_audit_log(
            self.db,
            request,
            action="volunteer.assign",
            resource_type="volunteer_assignment",
            resource_id=assignment.id,
            current_user=current_user,
            new_state={"user_id": assignment.user_id, "station_id": assignment.polling_station_id},
        )
        return assignment

    async def list_assignments(
        self,
        election_id: str,
        polling_station_id: Optional[str] = None,
    ) -> List[VolunteerAssignmentResponse]:
        stmt = (
            select(VolunteerAssignment)
            .options(
                selectinload(VolunteerAssignment.user),
                selectinload(VolunteerAssignment.polling_station),
            )
            .where(VolunteerAssignment.election_id == election_id)
        )
        if polling_station_id:
            stmt = stmt.where(VolunteerAssignment.polling_station_id == polling_station_id)

        result = await self.db.execute(stmt)
        assignments = result.scalars().all()

        responses = []
        for a in assignments:
            responses.append(
                VolunteerAssignmentResponse(
                    id=a.id,
                    user_id=a.user_id,
                    election_id=a.election_id,
                    polling_station_id=a.polling_station_id,
                    assigned_by=a.assigned_by,
                    shift_start=a.shift_start,
                    shift_end=a.shift_end,
                    task_role=a.task_role,
                    is_active=a.is_active,
                    notes=a.notes,
                    volunteer_name=a.user.full_name if a.user else None,
                    volunteer_email=a.user.email if a.user else None,
                    volunteer_phone=a.user.phone if a.user else None,
                    station_name=a.polling_station.name if a.polling_station else None,
                    created_at=a.created_at,
                )
            )
        return responses

    async def update_assignment(
        self,
        request: Request,
        assignment_id: str,
        update_in: Any,
        current_user: User,
    ) -> VolunteerAssignment:
        assignment = await self.assignment_repo.get_by_id(assignment_id)
        if not assignment:
            raise ResourceNotFoundException("VolunteerAssignment", "id", assignment_id)

        if hasattr(update_in, "is_active") and update_in.is_active is not None:
            assignment.is_active = update_in.is_active
        elif isinstance(update_in, dict) and "is_active" in update_in:
            assignment.is_active = update_in["is_active"]

        if hasattr(update_in, "task_role") and update_in.task_role:
            assignment.task_role = update_in.task_role
        elif isinstance(update_in, dict) and "task_role" in update_in:
            assignment.task_role = update_in["task_role"]

        if hasattr(update_in, "notes") and update_in.notes is not None:
            assignment.notes = update_in.notes
        elif isinstance(update_in, dict) and "notes" in update_in:
            assignment.notes = update_in["notes"]

        await self.db.commit()
        await self.db.refresh(assignment)
        return assignment

    def _to_profile_out(self, p: VolunteerProfile) -> VolunteerProfileOut:
        total = p.total_submissions or 0
        app_rate = round((p.approved_count / total * 100) if total > 0 else 0.0, 2)
        rej_rate = round((p.rejected_count / total * 100) if total > 0 else 0.0, 2)
        dup_rate = round((p.duplicate_count / total * 100) if total > 0 else 0.0, 2)
        achieve_pct = round((p.monthly_collection / p.monthly_target * 100) if p.monthly_target > 0 else 0.0, 2)

        return VolunteerProfileOut(
            id=p.id,
            user_id=p.user_id,
            organization_id=p.organization_id,
            volunteer_code=p.volunteer_code,
            profile_photo_url=p.profile_photo_url,
            name=p.user.full_name if p.user else "Volunteer",
            email=p.user.email if p.user else "",
            phone=p.user.phone if p.user else None,
            supervisor_id=p.supervisor_id,
            supervisor_name=p.supervisor.full_name if p.supervisor else None,
            election_id=p.election_id,
            constituency_id=p.constituency_id,
            ward_id=p.ward_id,
            booth_id=p.booth_id,
            area_id=p.area_id,
            polling_station_id=p.polling_station_id,
            daily_target=p.daily_target,
            weekly_target=p.weekly_target,
            monthly_target=p.monthly_target,
            daily_collection=p.daily_collection,
            weekly_collection=p.weekly_collection,
            monthly_collection=p.monthly_collection,
            total_submissions=p.total_submissions,
            approved_count=p.approved_count,
            rejected_count=p.rejected_count,
            duplicate_count=p.duplicate_count,
            approval_rate=app_rate,
            rejection_rate=rej_rate,
            duplicate_rate=dup_rate,
            achievement_percentage=achieve_pct,
            status=p.status,
            last_login_at=p.last_login_at,
            last_submission_at=p.last_submission_at,
            last_activity_at=p.last_activity_at,
            created_at=p.created_at,
        )
