from typing import List, Optional, Tuple

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.audit import record_audit_log
from app.core.exceptions import PermissionDeniedException, ResourceNotFoundException
from app.models.candidate import Candidate, CandidateStatus
from app.models.user import User
from app.repositories.base import BaseRepository
from app.schemas.candidate import CandidateCreate, CandidateStatusUpdateRequest, CandidateUpdate
from app.schemas.common import PaginationMeta


class CandidateService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.cand_repo = BaseRepository(Candidate, db)

    async def list_org_candidates(self, organization_id: Optional[str] = None) -> List[Candidate]:
        stmt = select(Candidate).options(selectinload(Candidate.documents))
        if organization_id:
            stmt = stmt.where(Candidate.organization_id == organization_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_candidate(self, request: Request, cand_in: CandidateCreate, current_user: Optional[User] = None) -> Candidate:
        full_name = cand_in.full_name or cand_in.name or "Candidate"
        org_id = current_user.organization_id if current_user else cand_in.election_id

        cand = Candidate(
            organization_id=org_id,
            election_id=cand_in.election_id,
            position_id=cand_in.position_id,
            constituency_id=cand_in.constituency_id,
            name=cand_in.name or full_name,
            hindiName=cand_in.hindiName or full_name,
            post=cand_in.post or ("Sarpanch (Gram Panchayat)" if cand_in.postType == "sarpanch" else "Panch (Ward)"),
            postType=cand_in.postType or "sarpanch",
            constituency_name=cand_in.constituency,
            symbol=cand_in.symbol or "🚜",
            symbolName=cand_in.symbolName or "Tractor",
            photo=cand_in.photo or cand_in.photo_url or "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=400&auto=format&fit=crop&q=80",
            slogan=cand_in.slogan or "गांव का समग्र विकास, हर घर विश्वास और खुशहाली!",
            votersCount=cand_in.votersCount or 0,
            volunteersCount=cand_in.volunteersCount or 0,
            manifesto=cand_in.manifesto or "",
            full_name=full_name.strip(),
            candidate_id_number=cand_in.candidate_id_number,
            party_name=cand_in.party_name or cand_in.symbolName,
            party_symbol_url=cand_in.party_symbol_url or cand_in.symbol,
            photo_url=cand_in.photo_url or cand_in.photo,
            phone=cand_in.phone,
            email=cand_in.email,
            display_order=cand_in.display_order or 0,
            status=CandidateStatus.APPROVED
        )
        cand = await self.cand_repo.create(cand)

        if current_user:
            await record_audit_log(
                self.db,
                request,
                action="candidate.create",
                resource_type="candidate",
                resource_id=cand.id,
                current_user=current_user,
                new_state={"full_name": cand.full_name, "status": cand.status.value}
            )
        return cand

    async def list_candidates(
        self,
        election_id: str,
        position_id: Optional[str] = None,
        constituency_id: Optional[str] = None,
        status: Optional[CandidateStatus] = None,
        page: int = 1,
        page_size: int = 50
    ) -> Tuple[List[Candidate], PaginationMeta]:
        filters = {"election_id": election_id}
        if position_id:
            filters["position_id"] = position_id
        if constituency_id:
            filters["constituency_id"] = constituency_id
        if status:
            filters["status"] = status

        return await self.cand_repo.list_paginated(
            page=page,
            page_size=page_size,
            filters=filters,
            search_fields=["full_name", "party_name", "candidate_id_number"]
        )

    async def get_candidate(self, cand_id: str) -> Candidate:
        stmt = (
            select(Candidate)
            .options(selectinload(Candidate.documents), selectinload(Candidate.position))
            .where(Candidate.id == cand_id)
        )
        result = await self.db.execute(stmt)
        cand = result.scalars().first()
        if not cand:
            raise ResourceNotFoundException("Candidate", cand_id)
        return cand

    async def update_candidate(self, request: Request, cand_id: str, cand_in: CandidateUpdate, current_user: User) -> Candidate:
        cand = await self.get_candidate(cand_id)
        if current_user.organization_id and cand.organization_id != current_user.organization_id:
            raise PermissionDeniedException(message="Cannot edit a candidate from another organization.")
        prev_state = {"full_name": cand.full_name, "party_name": cand.party_name}

        if cand_in.name is not None:
            cand.name = cand_in.name.strip()
            cand.full_name = cand_in.name.strip()
        if cand_in.hindiName is not None:
            cand.hindiName = cand_in.hindiName.strip()
        if cand_in.post is not None:
            cand.post = cand_in.post.strip()
        if cand_in.postType is not None:
            cand.postType = cand_in.postType
        if cand_in.constituency is not None:
            cand.constituency_name = cand_in.constituency.strip()
        if cand_in.symbol is not None:
            cand.symbol = cand_in.symbol
        if cand_in.symbolName is not None:
            cand.symbolName = cand_in.symbolName.strip()
        if cand_in.photo is not None:
            cand.photo = cand_in.photo
        if cand_in.slogan is not None:
            cand.slogan = cand_in.slogan.strip()
        if cand_in.votersCount is not None:
            cand.votersCount = cand_in.votersCount
        if cand_in.volunteersCount is not None:
            cand.volunteersCount = cand_in.volunteersCount
        if cand_in.full_name is not None:
            cand.full_name = cand_in.full_name.strip()
        if cand_in.candidate_id_number is not None:
            cand.candidate_id_number = cand_in.candidate_id_number
        if cand_in.party_name is not None:
            cand.party_name = cand_in.party_name
        if cand_in.party_symbol_url is not None:
            cand.party_symbol_url = cand_in.party_symbol_url
        if cand_in.photo_url is not None:
            cand.photo_url = cand_in.photo_url
        if cand_in.phone is not None:
            cand.phone = cand_in.phone
        if cand_in.email is not None:
            cand.email = cand_in.email
        if cand_in.manifesto is not None:
            cand.manifesto = cand_in.manifesto
        if cand_in.display_order is not None:
            cand.display_order = cand_in.display_order
        if cand_in.position_id is not None:
            cand.position_id = cand_in.position_id
        if cand_in.constituency_id is not None:
            cand.constituency_id = cand_in.constituency_id

        updated = await self.cand_repo.update(cand)

        await record_audit_log(
            self.db,
            request,
            action="candidate.update",
            resource_type="candidate",
            resource_id=cand.id,
            current_user=current_user,
            prev_state=prev_state,
            new_state={"full_name": updated.full_name}
        )
        return updated

    async def delete_candidate(self, request: Request, cand_id: str, current_user: User) -> bool:
        cand = await self.get_candidate(cand_id)
        if current_user.organization_id and cand.organization_id != current_user.organization_id:
            raise PermissionDeniedException(message="Cannot delete a candidate from another organization.")
        await self.db.delete(cand)
        await self.db.commit()
        await record_audit_log(
            self.db,
            request,
            action="candidate.delete",
            resource_type="candidate",
            resource_id=cand.id,
            current_user=current_user,
        )
        return True

    async def update_candidate_status(
        self,
        request: Request,
        cand_id: str,
        status_in: CandidateStatusUpdateRequest,
        current_user: User
    ) -> Candidate:
        cand = await self.get_candidate(cand_id)
        prev_status = cand.status

        cand.status = status_in.status
        cand.rejection_reason = status_in.rejection_reason
        if status_in.status == CandidateStatus.APPROVED:
            cand.approved_by = current_user.id

        updated = await self.cand_repo.update(cand)

        await record_audit_log(
            self.db,
            request,
            action=f"candidate.{status_in.status.value.lower()}",
            resource_type="candidate",
            resource_id=cand.id,
            current_user=current_user,
            prev_state={"status": prev_status.value},
            new_state={"status": updated.status.value, "rejection_reason": status_in.rejection_reason}
        )
        return updated
