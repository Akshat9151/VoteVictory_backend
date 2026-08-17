from typing import List, Optional
from fastapi import Request
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.audit import record_audit_log
from app.core.exceptions import ResourceNotFoundException
from app.models.polling_station import PollingStation, VolunteerAssignment
from app.models.user import User
from app.repositories.base import BaseRepository
from app.schemas.volunteer import VolunteerAssignmentCreate, VolunteerAssignmentResponse, VolunteerStatusUpdate


class VolunteerService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = BaseRepository(VolunteerAssignment, db)

    async def assign_volunteer(
        self,
        request: Request,
        assignment_in: VolunteerAssignmentCreate,
        current_user: User
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
            notes=assignment_in.notes
        )
        assignment = await self.repo.create(assignment)

        await record_audit_log(
            self.db,
            request,
            action="volunteer.assign",
            resource_type="volunteer_assignment",
            resource_id=assignment.id,
            current_user=current_user,
            new_state={"user_id": assignment.user_id, "station_id": assignment.polling_station_id}
        )
        return assignment

    async def list_assignments(
        self,
        election_id: str,
        polling_station_id: Optional[str] = None
    ) -> List[VolunteerAssignmentResponse]:
        stmt = (
            select(VolunteerAssignment)
            .options(
                selectinload(VolunteerAssignment.user),
                selectinload(VolunteerAssignment.polling_station)
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
                    created_at=a.created_at
                )
            )
        return responses

    async def update_status(
        self,
        request: Request,
        assignment_id: str,
        update_in: VolunteerStatusUpdate,
        current_user: User
    ) -> VolunteerAssignment:
        assignment = await self.repo.get_by_id(assignment_id)
        if not assignment:
            raise ResourceNotFoundException("VolunteerAssignment", assignment_id)

        assignment.is_active = update_in.is_active
        if update_in.task_role:
            assignment.task_role = update_in.task_role
        if update_in.notes:
            assignment.notes = update_in.notes

        updated = await self.repo.update(assignment)

        await record_audit_log(
            self.db,
            request,
            action="volunteer.assignment_update",
            resource_type="volunteer_assignment",
            resource_id=assignment.id,
            current_user=current_user,
            new_state={"is_active": updated.is_active}
        )
        return updated
