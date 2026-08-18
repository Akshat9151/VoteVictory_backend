from datetime import datetime, timezone
from typing import List, Optional, Tuple

from fastapi import Request
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.audit import record_audit_log
from app.core.exceptions import ResourceNotFoundException
from app.models.data_collection import (
    DataDuplicate,
    DataSubmission,
    DuplicateResolutionStatus,
    DuplicateSignal,
    SubmissionStatus,
)
from app.models.user import User
from app.schemas.data_collection import DataDuplicateOut, DuplicateResolveRequest


class DuplicateDetectionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def scan_and_flag_duplicates(
        self,
        submission: DataSubmission,
    ) -> Optional[DataDuplicate]:
        """
        Evaluates multi-signal duplicate criteria against existing submissions in the organization.
        Signals:
        1. Exact Mobile match
        2. Exact Voter ID / Card match
        3. Exact Email match
        4. Name + Area / Booth match
        """
        # Exclude self
        stmt = (
            select(DataSubmission)
            .where(
                DataSubmission.organization_id == submission.organization_id,
                DataSubmission.id != submission.id,
            )
        )

        match_found = None
        match_signal = None
        match_reason = ""
        similarity_score = 1.0

        # Check 1: Mobile
        if submission.mobile:
            mobile_stmt = stmt.where(DataSubmission.mobile == submission.mobile)
            matched = (await self.db.execute(mobile_stmt)).scalars().first()
            if matched:
                match_found = matched
                match_signal = DuplicateSignal.MOBILE
                match_reason = f"Exact mobile number match: {submission.mobile}"

        # Check 2: Voter Card Number
        if not match_found and submission.voter_card_number:
            voter_id_stmt = stmt.where(DataSubmission.voter_card_number == submission.voter_card_number)
            matched = (await self.db.execute(voter_id_stmt)).scalars().first()
            if matched:
                match_found = matched
                match_signal = DuplicateSignal.VOTER_ID
                match_reason = f"Exact voter ID number match: {submission.voter_card_number}"

        # Check 3: Email
        if not match_found and submission.email:
            email_stmt = stmt.where(DataSubmission.email.ilike(submission.email))
            matched = (await self.db.execute(email_stmt)).scalars().first()
            if matched:
                match_found = matched
                match_signal = DuplicateSignal.EMAIL
                match_reason = f"Exact email address match: {submission.email}"

        # Check 4: Name + Area/Booth
        if not match_found and submission.citizen_name:
            name_stmt = stmt.where(
                DataSubmission.citizen_name.ilike(submission.citizen_name),
                DataSubmission.booth_no == submission.booth_no,
            )
            matched = (await self.db.execute(name_stmt)).scalars().first()
            if matched:
                match_found = matched
                match_signal = DuplicateSignal.NAME_AREA
                match_reason = f"Same citizen name '{submission.citizen_name}' in Booth '{submission.booth_no}'"
                similarity_score = 0.85

        if match_found:
            duplicate_record = DataDuplicate(
                organization_id=submission.organization_id,
                record_a_id=match_found.id,
                record_b_id=submission.id,
                match_signal=match_signal,
                similarity_score=similarity_score,
                match_reason=match_reason,
                resolution_status=DuplicateResolutionStatus.POSSIBLE_DUPLICATE,
            )
            self.db.add(duplicate_record)
            submission.is_flagged_duplicate = True
            submission.status = SubmissionStatus.DUPLICATE
            await self.db.flush()
            return duplicate_record

        return None

    async def list_duplicates(
        self,
        organization_id: Optional[str] = None,
        resolution_status: Optional[DuplicateResolutionStatus] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[DataDuplicateOut], int]:
        stmt = (
            select(DataDuplicate)
            .options(
                selectinload(DataDuplicate.record_a).selectinload(DataSubmission.quality_check),
                selectinload(DataDuplicate.record_a).selectinload(DataSubmission.volunteer),
                selectinload(DataDuplicate.record_b).selectinload(DataSubmission.quality_check),
                selectinload(DataDuplicate.record_b).selectinload(DataSubmission.volunteer),
            )
        )
        if organization_id:
            stmt = stmt.where(DataDuplicate.organization_id == organization_id)
        if resolution_status:
            stmt = stmt.where(DataDuplicate.resolution_status == resolution_status)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_stmt)).scalar_one()

        stmt = stmt.order_by(desc(DataDuplicate.created_at)).offset(skip).limit(limit)
        results = (await self.db.execute(stmt)).scalars().all()

        return [DataDuplicateOut.model_validate(d) for d in results], total

    async def resolve_duplicate(
        self,
        request: Request,
        resolve_in: DuplicateResolveRequest,
        current_user: User,
    ) -> DataDuplicateOut:
        stmt = (
            select(DataDuplicate)
            .options(
                selectinload(DataDuplicate.record_a).selectinload(DataSubmission.quality_check),
                selectinload(DataDuplicate.record_a).selectinload(DataSubmission.volunteer),
                selectinload(DataDuplicate.record_b).selectinload(DataSubmission.quality_check),
                selectinload(DataDuplicate.record_b).selectinload(DataSubmission.volunteer),
            )
            .where(DataDuplicate.id == resolve_in.duplicate_id)
        )
        duplicate = (await self.db.execute(stmt)).scalar_one_or_none()
        if not duplicate:
            raise ResourceNotFoundException("DataDuplicate", resolve_in.duplicate_id)

        duplicate.resolution_status = resolve_in.action
        duplicate.resolved_by = current_user.id
        duplicate.resolved_at = datetime.now(timezone.utc)
        duplicate.resolution_notes = resolve_in.resolution_notes

        # Handle Merge or Rejection actions
        if resolve_in.action == DuplicateResolutionStatus.MERGED:
            if resolve_in.primary_record_id == duplicate.record_a_id:
                duplicate.record_a.status = SubmissionStatus.APPROVED
                duplicate.record_b.status = SubmissionStatus.REJECTED
                duplicate.record_b.rejection_reason = "Merged into primary record"
            else:
                duplicate.record_b.status = SubmissionStatus.APPROVED
                duplicate.record_a.status = SubmissionStatus.REJECTED
                duplicate.record_a.rejection_reason = "Merged into primary record"
        elif resolve_in.action == DuplicateResolutionStatus.KEPT_SEPARATE:
            if duplicate.record_b.status == SubmissionStatus.DUPLICATE:
                duplicate.record_b.status = SubmissionStatus.UNDER_REVIEW
                duplicate.record_b.is_flagged_duplicate = False
        elif resolve_in.action == DuplicateResolutionStatus.REJECTED:
            duplicate.record_b.status = SubmissionStatus.REJECTED
            duplicate.record_b.rejection_reason = "Rejected as duplicate record"

        await self.db.commit()

        await record_audit_log(
            self.db,
            request,
            action="data.duplicate_resolve",
            resource_type="data_duplicate",
            resource_id=duplicate.id,
            current_user=current_user,
            new_state={"action": str(resolve_in.action)},
        )

        return DataDuplicateOut.model_validate(duplicate)
