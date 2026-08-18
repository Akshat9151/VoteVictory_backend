from typing import List

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit_log
from app.core.exceptions import ResourceNotFoundException
from app.models.election import Position
from app.models.user import User
from app.repositories.base import BaseRepository
from app.schemas.position import PositionCreate, PositionUpdate


class PositionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.position_repo = BaseRepository(Position, db)

    async def create_position(self, request: Request, pos_in: PositionCreate, current_user: User) -> Position:
        pos = Position(
            election_id=pos_in.election_id,
            constituency_id=pos_in.constituency_id,
            title=pos_in.title.strip(),
            description=pos_in.description,
            min_selections=pos_in.min_selections,
            max_selections=pos_in.max_selections,
            candidate_limit=pos_in.candidate_limit,
            display_order=pos_in.display_order,
            is_active=pos_in.is_active
        )
        pos = await self.position_repo.create(pos)

        await record_audit_log(
            self.db,
            request,
            action="position.create",
            resource_type="position",
            resource_id=pos.id,
            current_user=current_user,
            new_state={"title": pos.title, "election_id": pos.election_id}
        )
        return pos

    async def list_positions(self, election_id: str) -> List[Position]:
        stmt = select(Position).where(Position.election_id == election_id).order_by(Position.display_order.asc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_position(self, request: Request, pos_id: str, pos_in: PositionUpdate, current_user: User) -> Position:
        pos = await self.position_repo.get_by_id(pos_id)
        if not pos:
            raise ResourceNotFoundException("Position", pos_id)

        if pos_in.title is not None:
            pos.title = pos_in.title.strip()
        if pos_in.description is not None:
            pos.description = pos_in.description
        if pos_in.min_selections is not None:
            pos.min_selections = pos_in.min_selections
        if pos_in.max_selections is not None:
            pos.max_selections = pos_in.max_selections
        if pos_in.candidate_limit is not None:
            pos.candidate_limit = pos_in.candidate_limit
        if pos_in.display_order is not None:
            pos.display_order = pos_in.display_order
        if pos_in.is_active is not None:
            pos.is_active = pos_in.is_active
        if pos_in.constituency_id is not None:
            pos.constituency_id = pos_in.constituency_id

        updated = await self.position_repo.update(pos)

        await record_audit_log(
            self.db,
            request,
            action="position.update",
            resource_type="position",
            resource_id=pos.id,
            current_user=current_user,
            new_state={"title": updated.title}
        )
        return updated
