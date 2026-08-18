from datetime import datetime
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_audit_event
from app.models.team import TeamMember
from app.models.user import User
from app.repositories.booth_repo import BoothRepository
from app.repositories.team_repo import TeamMemberRepository, VolunteerRepository
from app.schemas.booth import BoothResponse
from app.schemas.team import TeamMemberCreate, TeamMemberResponse
from app.schemas.volunteer import VolunteerResponse


class TeamService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.team_repo = TeamMemberRepository(db)
        self.vol_repo = VolunteerRepository(db)
        self.booth_repo = BoothRepository(db)

    async def get_team_members(self, organization_id: str) -> List[TeamMemberResponse]:
        members = await self.team_repo.list_all(organization_id=organization_id)
        return [
            TeamMemberResponse(
                id=m.id,
                name=m.name,
                role=m.role,
                roleTitle=m.roleTitle,
                ward=m.ward,
                phone=m.phone,
                status=m.status,
                votersHandled=m.votersHandled,
                addedDate=m.addedDate
            )
            for m in members
        ]

    async def add_team_member(
        self,
        data: TeamMemberCreate,
        organization_id: str,
        user: Optional[User] = None,
        ip_address: Optional[str] = None
    ) -> TeamMemberResponse:
        added_date_str = datetime.now().strftime("%d %b %Y")
        member = TeamMember(
            organization_id=organization_id,
            name=data.name,
            role=data.role,
            roleTitle=data.roleTitle,
            ward=data.ward,
            phone=data.phone,
            status=data.status or "Active",
            votersHandled=0,
            addedDate=added_date_str
        )
        await self.team_repo.create(member)
        await log_audit_event(
            db=self.db,
            action="TEAM_MEMBER_ADD",
            entity_type="team_member",
            entity_id=member.id,
            organization_id=organization_id,
            user=user,
            details=f"Added team member {member.name} ({member.role})",
            ip_address=ip_address
        )
        await self.db.commit()

        return TeamMemberResponse(
            id=member.id,
            name=member.name,
            role=member.role,
            roleTitle=member.roleTitle,
            ward=member.ward,
            phone=member.phone,
            status=member.status,
            votersHandled=member.votersHandled,
            addedDate=member.addedDate
        )

    async def get_volunteers(self, organization_id: str) -> List[VolunteerResponse]:
        volunteers = await self.vol_repo.list_all(organization_id=organization_id)
        return [
            VolunteerResponse(
                id=v.id,
                name=v.name,
                role=v.role,
                ward=v.ward,
                phone=v.phone,
                votersAdded=v.votersAdded,
                callsMade=v.callsMade,
                slipsDistributed=v.slipsDistributed,
                status=v.status
            )
            for v in volunteers
        ]

    async def get_booths(self, organization_id: str) -> List[BoothResponse]:
        booths = await self.booth_repo.list_all(organization_id=organization_id)
        return [
            BoothResponse(
                boothNo=b.boothNo,
                location=b.location,
                incharge=b.incharge,
                voters=b.voters,
                slips=b.slips,
                coverage=b.coverage
            )
            for b in booths
        ]
