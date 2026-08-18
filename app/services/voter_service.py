from datetime import datetime
from typing import List, Optional, Tuple

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit_log
from app.core.exceptions import ResourceNotFoundException
from app.models.user import User
from app.models.voter import Voter, VoterStatus, VoterVerification, VotingStatus
from app.repositories.voter_repo import VoterRepository
from app.schemas.common import PaginationMeta
from app.schemas.voter import (
    VoterCreate,
    VoterFilterParams,
    VoterUpdate,
    VoterVerificationRequest,
    VoterVerificationResponse,
)


class VoterService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.voter_repo = VoterRepository(db)

    async def list_org_voters(self, organization_id: Optional[str] = None) -> List[Voter]:
        stmt = select(Voter)
        if organization_id:
            stmt = stmt.where(Voter.organization_id == organization_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_audience_split(self, organization_id: Optional[str] = None) -> dict:
        voters = await self.list_org_voters(organization_id)
        if not voters:
            voters = await self.list_org_voters(None)

        total = len(voters)
        whatsapp = sum(1 for v in voters if v.channel == "WhatsApp" and v.mobile)
        sms = sum(1 for v in voters if v.channel != "WhatsApp" or not v.mobile)
        denom = total if total > 0 else 1
        return {
            "total": total,
            "whatsapp": whatsapp,
            "sms": sms,
            "whatsappPercent": round((whatsapp / denom) * 100),
            "smsPercent": round((sms / denom) * 100)
        }

    async def create_voter(self, request: Optional[Request], voter_in: VoterCreate, current_user: Optional[User] = None) -> Voter:
        org_id = current_user.organization_id if current_user else "default_org"
        voter_name = voter_in.name or f"{voter_in.first_name or ''} {voter_in.last_name or ''}".strip() or "Voter"
        voter_id_num = voter_in.voter_id_number or f"V-{voter_in.ward or '01'}-{int(datetime.now().timestamp()) % 10000}"

        voter = Voter(
            id=voter_id_num,
            organization_id=org_id,
            election_id=voter_in.election_id,
            constituency_id=voter_in.constituency_id,
            polling_station_id=voter_in.polling_station_id,
            name=voter_name,
            voter_id_number=voter_id_num,
            first_name=voter_in.first_name or voter_name.split()[0],
            last_name=voter_in.last_name or (" ".join(voter_name.split()[1:]) if len(voter_name.split()) > 1 else ""),
            father_or_spouse_name=voter_in.father_or_spouse_name,
            date_of_birth=voter_in.date_of_birth,
            age=voter_in.age or 35,
            gender=voter_in.gender or "Male",
            mobile=voter_in.mobile or voter_in.phone_number or "",
            phone_number=voter_in.phone_number or voter_in.mobile or "",
            email=voter_in.email,
            address=voter_in.address or voter_in.house or "",
            house_number=voter_in.house_number or voter_in.house or "",
            ward=voter_in.ward or voter_in.ward_name or "Ward 01",
            ward_name=voter_in.ward_name or voter_in.ward or "Ward 01",
            channel=voter_in.channel or "WhatsApp",
            consent=voter_in.consent or "Verified",
            source=voter_in.source or "Official Roll",
            status=voter_in.status or "Valid",
            voting_status=VotingStatus.NOT_VOTED,
            has_voted=False,
            notes=voter_in.notes
        )
        voter = await self.voter_repo.create(voter)

        if current_user and request:
            await record_audit_log(
                self.db,
                request,
                action="voter.create",
                resource_type="voter",
                resource_id=voter.id,
                current_user=current_user,
                organization_id=org_id,
                new_state={"voter_id_number": voter.voter_id_number, "name": voter.name}
            )
        return voter

    async def create_batch(self, request: Optional[Request], voters_in: List[VoterCreate], current_user: Optional[User] = None) -> List[Voter]:
        created: List[Voter] = []
        for idx, v_in in enumerate(voters_in):
            voter = await self.create_voter(request, v_in, current_user)
            created.append(voter)
        return created

    async def list_voters(
        self,
        election_id: str,
        current_user: User,
        filters: VoterFilterParams,
        page: int = 1,
        page_size: int = 20,
        assigned_station_id: Optional[str] = None
    ) -> Tuple[List[Voter], PaginationMeta]:
        stmt_filters = {"election_id": election_id}

        # Station restriction for volunteer
        if assigned_station_id:
            stmt_filters["polling_station_id"] = assigned_station_id
        elif filters.polling_station_id:
            stmt_filters["polling_station_id"] = filters.polling_station_id

        if filters.status:
            stmt_filters["status"] = filters.status
        if filters.voting_status:
            stmt_filters["voting_status"] = filters.voting_status
        if filters.constituency_id:
            stmt_filters["constituency_id"] = filters.constituency_id
        if filters.ward_name:
            stmt_filters["ward_name"] = filters.ward_name
        if filters.has_voted is not None:
            stmt_filters["has_voted"] = filters.has_voted

        return await self.voter_repo.list_paginated(
            page=page,
            page_size=page_size,
            filters=stmt_filters,
            search_query=filters.search,
            search_fields=["first_name", "last_name", "voter_id_number", "phone_number", "ward_name"]
        )

    async def get_voter(self, voter_id: str) -> Voter:
        voter = await self.voter_repo.get_by_id(voter_id)
        if not voter:
            raise ResourceNotFoundException("Voter", voter_id)
        return voter

    async def update_voter(self, request: Request, voter_id: str, voter_in: VoterUpdate, current_user: User) -> Voter:
        voter = await self.get_voter(voter_id)
        prev_state = {"first_name": voter.first_name, "status": voter.status.value}

        if voter_in.first_name is not None:
            voter.first_name = voter_in.first_name.strip()
        if voter_in.last_name is not None:
            voter.last_name = voter_in.last_name.strip()
        if voter_in.father_or_spouse_name is not None:
            voter.father_or_spouse_name = voter_in.father_or_spouse_name
        if voter_in.date_of_birth is not None:
            voter.date_of_birth = voter_in.date_of_birth
        if voter_in.age is not None:
            voter.age = voter_in.age
        if voter_in.gender is not None:
            voter.gender = voter_in.gender
        if voter_in.phone_number is not None:
            voter.phone_number = voter_in.phone_number
        if voter_in.email is not None:
            voter.email = voter_in.email
        if voter_in.address is not None:
            voter.address = voter_in.address
        if voter_in.house_number is not None:
            voter.house_number = voter_in.house_number
        if voter_in.ward_name is not None:
            voter.ward_name = voter_in.ward_name
        if voter_in.status is not None:
            voter.status = voter_in.status
        if voter_in.constituency_id is not None:
            voter.constituency_id = voter_in.constituency_id
        if voter_in.polling_station_id is not None:
            voter.polling_station_id = voter_in.polling_station_id
        if voter_in.notes is not None:
            voter.notes = voter_in.notes

        updated = await self.voter_repo.update(voter)

        await record_audit_log(
            self.db,
            request,
            action="voter.update",
            resource_type="voter",
            resource_id=voter.id,
            current_user=current_user,
            prev_state=prev_state,
            new_state={"first_name": updated.first_name, "status": updated.status.value}
        )
        return updated

    async def verify_voter(
        self,
        request: Request,
        voter_id: str,
        verify_in: VoterVerificationRequest,
        current_user: User
    ) -> VoterVerificationResponse:
        voter = await self.get_voter(voter_id)

        verification = VoterVerification(
            voter_id=voter.id,
            verification_method=verify_in.verification_method,
            is_verified=True,
            verified_by_user_id=current_user.id,
            id_document_type=verify_in.id_document_type,
            id_document_number=verify_in.id_document_number
        )
        self.db.add(verification)

        voter.status = VoterStatus.VERIFIED
        await self.voter_repo.update(voter)

        await record_audit_log(
            self.db,
            request,
            action="voter.verify",
            resource_type="voter",
            resource_id=voter.id,
            current_user=current_user,
            new_state={"status": VoterStatus.VERIFIED.value, "method": verify_in.verification_method}
        )

        return VoterVerificationResponse(
            voter_id=voter.id,
            is_verified=True,
            verification_method=verify_in.verification_method,
            message="Voter identity successfully verified."
        )
