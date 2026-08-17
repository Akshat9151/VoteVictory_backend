from typing import List, Optional
from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.audit import record_audit_log
from app.core.exceptions import ResourceNotFoundException
from app.models.election import Constituency
from app.models.user import User
from app.repositories.base import BaseRepository
from app.schemas.constituency import ConstituencyCreate, ConstituencyUpdate


class ConstituencyService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = BaseRepository(Constituency, db)

    async def create_constituency(self, request: Request, con_in: ConstituencyCreate, current_user: User) -> Constituency:
        con = Constituency(
            election_id=con_in.election_id,
            name=con_in.name.strip(),
            code=con_in.code.strip() if con_in.code else None,
            description=con_in.description
        )
        con = await self.repo.create(con)

        await record_audit_log(
            self.db,
            request,
            action="constituency.create",
            resource_type="constituency",
            resource_id=con.id,
            current_user=current_user,
            new_state={"name": con.name, "election_id": con.election_id}
        )
        return con

    async def list_constituencies(self, election_id: str) -> List[Constituency]:
        stmt = select(Constituency).where(Constituency.election_id == election_id).order_by(Constituency.name.asc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_constituency(self, request: Request, con_id: str, con_in: ConstituencyUpdate, current_user: User) -> Constituency:
        con = await self.repo.get_by_id(con_id)
        if not con:
            raise ResourceNotFoundException("Constituency", con_id)

        if con_in.name is not None:
            con.name = con_in.name.strip()
        if con_in.code is not None:
            con.code = con_in.code.strip()
        if con_in.description is not None:
            con.description = con_in.description

        updated = await self.repo.update(con)

        await record_audit_log(
            self.db,
            request,
            action="constituency.update",
            resource_type="constituency",
            resource_id=con.id,
            current_user=current_user,
            new_state={"name": updated.name}
        )
        return updated
