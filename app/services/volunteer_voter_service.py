import random
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit_log
from app.core.exceptions import NotFoundException
from app.models.user import User
from app.models.volunteer_voter import VolunteerVoter
from app.repositories.volunteer_voter_repo import VolunteerVoterRepository
from app.schemas.volunteer_voter import (
    VolunteerVoterCreate,
    VolunteerVoterResponse,
    VolunteerVoterStatusUpdate,
)


class VolunteerVoterService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = VolunteerVoterRepository(db)

    async def get_volunteer_voters(self, organization_id: Optional[str] = None) -> List[VolunteerVoterResponse]:
        filters = {"organization_id": organization_id} if organization_id else None
        voters = await self.repo.list_all(filters=filters)
        return [
            VolunteerVoterResponse(
                id=v.id,
                name=v.name,
                age=v.age,
                mobile=v.mobile,
                house=v.house,
                status=v.status,
                slipHanded=v.slipHanded
            )
            for v in voters
        ]

    async def add_volunteer_voter(
        self,
        data: VolunteerVoterCreate,
        organization_id: str,
        user: Optional[User] = None,
        ip_address: Optional[str] = None
    ) -> VolunteerVoterResponse:
        voter_id = f"V-02-{random.randint(100, 999)}"
        voter = VolunteerVoter(
            id=voter_id,
            organization_id=organization_id,
            name=data.name,
            age=data.age,
            mobile=data.mobile or "",
            house=data.house or "",
            status=data.status or "Pending",
            slipHanded=bool(data.slipHanded)
        )
        await self.repo.create(voter)
        await record_audit_log(
            db=self.db,
            action="VOLUNTEER_VOTER_ADD",
            resource_type="volunteer_voter",
            resource_id=voter.id,
            organization_id=organization_id,
            current_user=user,
            details={"message": f"Added volunteer voter record {voter.name}", "ip_address": ip_address}
        )
        await self.db.commit()

        return VolunteerVoterResponse(
            id=voter.id,
            name=voter.name,
            age=voter.age,
            mobile=voter.mobile,
            house=voter.house,
            status=voter.status,
            slipHanded=voter.slipHanded
        )

    async def update_status(
        self,
        id: str,
        data: VolunteerVoterStatusUpdate,
        organization_id: str,
        user: Optional[User] = None,
        ip_address: Optional[str] = None
    ) -> VolunteerVoterResponse:
        voter = await self.repo.get_by_id(id=id, organization_id=organization_id)
        if not voter:
            raise NotFoundException(f"Volunteer voter with ID '{id}' not found.")

        old_status = voter.status
        voter.status = data.status
        if data.slipHanded is not None:
            voter.slipHanded = data.slipHanded

        await self.repo.update(voter)
        await record_audit_log(
            db=self.db,
            action="VOLUNTEER_VOTER_STATUS_UPDATE",
            resource_type="volunteer_voter",
            resource_id=voter.id,
            organization_id=organization_id,
            current_user=user,
            details={
                "message": f"Updated status from '{old_status}' to '{data.status}', slipHanded={voter.slipHanded}",
                "ip_address": ip_address
            }
        )
        await self.db.commit()

        return VolunteerVoterResponse(
            id=voter.id,
            name=voter.name,
            age=voter.age,
            mobile=voter.mobile,
            house=voter.house,
            status=voter.status,
            slipHanded=voter.slipHanded
        )
