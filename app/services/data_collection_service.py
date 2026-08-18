import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import Request
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.audit import record_audit_log
from app.core.exceptions import ResourceNotFoundException
from app.models.data_collection import (
    DataQualityCheck,
    DataReview,
    DataSubmission,
    ReviewAction,
    SubmissionStatus,
)
from app.models.election import Election
from app.models.organization import Organization
from app.models.user import User
from app.models.volunteer import ActivityType, VolunteerActivity, VolunteerProfile
from app.schemas.data_collection import (
    BulkReviewRequest,
    DataQualityStatsOut,
    DataReviewRequest,
    DataSubmissionCreate,
    DataSubmissionOut,
)
from app.services.duplicate_detection_service import DuplicateDetectionService


class DataCollectionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.duplicate_service = DuplicateDetectionService(db)

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

    async def submit_field_data(
        self,
        request: Request,
        submission_in: DataSubmissionCreate,
        current_user: User,
    ) -> DataSubmissionOut:
        org_id = await self._resolve_org_id(current_user, submission_in.election_id)

        # Create Data Submission model
        submission = DataSubmission(
            organization_id=org_id,
            election_id=submission_in.election_id,
            volunteer_id=current_user.id,
            constituency_id=submission_in.constituency_id,
            ward_id=submission_in.ward_id,
            booth_id=submission_in.booth_id,
            area_id=submission_in.area_id,
            citizen_name=submission_in.citizen_name.strip(),
            mobile=submission_in.mobile.strip() if submission_in.mobile else None,
            email=submission_in.email.strip() if submission_in.email else None,
            voter_card_number=submission_in.voter_card_number.strip().upper() if submission_in.voter_card_number else None,
            date_of_birth=submission_in.date_of_birth,
            gender=submission_in.gender,
            address_line=submission_in.address_line,
            ward_no=submission_in.ward_no,
            booth_no=submission_in.booth_no,
            preferred_party_candidate=submission_in.preferred_party_candidate,
            issues_concerns=submission_in.issues_concerns,
            custom_fields_json=json.dumps(submission_in.custom_fields) if submission_in.custom_fields else None,
            status=SubmissionStatus.SUBMITTED,
            submission_channel=submission_in.submission_channel,
        )
        self.db.add(submission)
        await self.db.flush()

        # Quality scoring
        quality_check = self._evaluate_quality(submission)
        quality_check.submission_id = submission.id
        self.db.add(quality_check)
        submission.quality_score = quality_check.quality_percentage

        # Duplicate scan
        await self.duplicate_service.scan_and_flag_duplicates(submission)

        # Update volunteer profile counters if submitted by a volunteer
        stmt = select(VolunteerProfile).where(VolunteerProfile.user_id == current_user.id)
        profile = (await self.db.execute(stmt)).scalar_one_or_none()
        if profile:
            profile.daily_collection = (profile.daily_collection or 0) + 1
            profile.weekly_collection = (profile.weekly_collection or 0) + 1
            profile.monthly_collection = (profile.monthly_collection or 0) + 1
            profile.total_submissions = (profile.total_submissions or 0) + 1
            profile.last_submission_at = datetime.now(timezone.utc)
            profile.last_activity_at = datetime.now(timezone.utc)
            if submission.is_flagged_duplicate:
                profile.duplicate_count = (profile.duplicate_count or 0) + 1

            # Log activity
            activity = VolunteerActivity(
                organization_id=org_id,
                volunteer_profile_id=profile.id,
                activity_type=ActivityType.SUBMISSION,
                description=f"Submitted field record for {submission.citizen_name}",
            )
            self.db.add(activity)

        await self.db.commit()

        await record_audit_log(
            self.db,
            request,
            action="data.submit",
            resource_type="data_submission",
            resource_id=submission.id,
            current_user=current_user,
            new_state={"citizen_name": submission.citizen_name, "status": str(submission.status)},
        )

        return await self.get_submission(submission.id)

    async def list_submissions(
        self,
        organization_id: Optional[str] = None,
        election_id: Optional[str] = None,
        volunteer_id: Optional[str] = None,
        booth_id: Optional[str] = None,
        area_id: Optional[str] = None,
        status: Optional[SubmissionStatus] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[DataSubmissionOut], int]:
        stmt = (
            select(DataSubmission)
            .options(
                selectinload(DataSubmission.volunteer),
                selectinload(DataSubmission.quality_check),
            )
        )
        if organization_id:
            stmt = stmt.where(DataSubmission.organization_id == organization_id)
        if election_id:
            stmt = stmt.where(DataSubmission.election_id == election_id)
        if volunteer_id:
            stmt = stmt.where(DataSubmission.volunteer_id == volunteer_id)
        if booth_id:
            stmt = stmt.where(DataSubmission.booth_id == booth_id)
        if area_id:
            stmt = stmt.where(DataSubmission.area_id == area_id)
        if status:
            stmt = stmt.where(DataSubmission.status == status)

        if search:
            search_pattern = f"%{search}%"
            stmt = stmt.where(
                (DataSubmission.citizen_name.ilike(search_pattern))
                | (DataSubmission.mobile.ilike(search_pattern))
                | (DataSubmission.email.ilike(search_pattern))
                | (DataSubmission.voter_card_number.ilike(search_pattern))
            )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_stmt)).scalar_one()

        stmt = stmt.order_by(desc(DataSubmission.created_at)).offset(skip).limit(limit)
        results = (await self.db.execute(stmt)).scalars().all()

        return [self._to_submission_out(s) for s in results], total

    async def get_submission(self, submission_id: str) -> DataSubmissionOut:
        stmt = (
            select(DataSubmission)
            .options(
                selectinload(DataSubmission.volunteer),
                selectinload(DataSubmission.quality_check),
            )
            .where(DataSubmission.id == submission_id)
        )
        sub = (await self.db.execute(stmt)).scalar_one_or_none()
        if not sub:
            raise ResourceNotFoundException("DataSubmission", submission_id)

        return self._to_submission_out(sub)

    async def review_submission(
        self,
        request: Request,
        submission_id: str,
        review_in: DataReviewRequest,
        current_user: User,
    ) -> DataSubmissionOut:
        stmt = (
            select(DataSubmission)
            .options(
                selectinload(DataSubmission.volunteer),
                selectinload(DataSubmission.quality_check),
            )
            .where(DataSubmission.id == submission_id)
        )
        submission = (await self.db.execute(stmt)).scalar_one_or_none()
        if not submission:
            raise ResourceNotFoundException("DataSubmission", submission_id)

        prev_status = submission.status
        new_status = SubmissionStatus.APPROVED if review_in.action == ReviewAction.APPROVE else SubmissionStatus.REJECTED

        submission.status = new_status
        submission.reviewed_by = current_user.id
        submission.reviewed_at = datetime.now(timezone.utc)
        submission.review_remarks = review_in.remarks
        submission.rejection_reason = review_in.reason

        # Create DataReview audit entry
        review_log = DataReview(
            submission_id=submission.id,
            reviewer_id=current_user.id,
            action=review_in.action,
            previous_status=prev_status,
            new_status=new_status,
            remarks=review_in.remarks,
            reason=review_in.reason,
        )
        self.db.add(review_log)

        # Update volunteer stats
        if submission.volunteer_id:
            profile_stmt = select(VolunteerProfile).where(VolunteerProfile.user_id == submission.volunteer_id)
            profile = (await self.db.execute(profile_stmt)).scalar_one_or_none()
            if profile:
                if new_status == SubmissionStatus.APPROVED:
                    profile.approved_count = (profile.approved_count or 0) + 1
                elif new_status == SubmissionStatus.REJECTED:
                    profile.rejected_count = (profile.rejected_count or 0) + 1

        await self.db.commit()

        await record_audit_log(
            self.db,
            request,
            action="data.review",
            resource_type="data_submission",
            resource_id=submission.id,
            current_user=current_user,
            new_state={"status": str(new_status), "remarks": review_in.remarks},
        )

        return self._to_submission_out(submission)

    async def bulk_review_submissions(
        self,
        request: Request,
        bulk_in: BulkReviewRequest,
        current_user: User,
    ) -> Dict[str, Any]:
        stmt = select(DataSubmission).where(DataSubmission.id.in_(bulk_in.submission_ids))
        if current_user.organization_id:
            stmt = stmt.where(DataSubmission.organization_id == current_user.organization_id)

        submissions = (await self.db.execute(stmt)).scalars().all()

        target_status = SubmissionStatus.APPROVED if bulk_in.action == ReviewAction.APPROVE else SubmissionStatus.REJECTED
        updated_count = 0

        for s in submissions:
            prev_status = s.status
            s.status = target_status
            s.reviewed_by = current_user.id
            s.reviewed_at = datetime.now(timezone.utc)
            s.review_remarks = bulk_in.remarks
            s.rejection_reason = bulk_in.reason

            review_log = DataReview(
                submission_id=s.id,
                reviewer_id=current_user.id,
                action=bulk_in.action,
                previous_status=prev_status,
                new_status=target_status,
                remarks=bulk_in.remarks,
                reason=bulk_in.reason,
            )
            self.db.add(review_log)
            updated_count += 1

        await self.db.commit()

        await record_audit_log(
            self.db,
            request,
            action="data.bulk_review",
            resource_type="data_submission",
            resource_id="bulk",
            current_user=current_user,
            new_state={"count": updated_count, "status": str(target_status)},
        )

        return {"status": "success", "processed_count": updated_count, "target_status": str(target_status)}

    async def get_quality_statistics(self, organization_id: Optional[str] = None) -> DataQualityStatsOut:
        stmt = select(DataSubmission)
        if organization_id:
            stmt = stmt.where(DataSubmission.organization_id == organization_id)
        results = (await self.db.execute(stmt)).scalars().all()

        total = len(results)
        if total == 0:
            return DataQualityStatsOut(
                total_records=0,
                valid_records=0,
                invalid_records=0,
                duplicate_records=0,
                incomplete_records=0,
                approved_records=0,
                pending_records=0,
                rejected_records=0,
                data_quality_percentage=100.0,
                duplicate_percentage=0.0,
                approval_percentage=0.0,
                rejection_percentage=0.0,
            )

        approved = sum(1 for s in results if s.status == SubmissionStatus.APPROVED)
        rejected = sum(1 for s in results if s.status == SubmissionStatus.REJECTED)
        duplicates = sum(1 for s in results if s.status == SubmissionStatus.DUPLICATE or s.is_flagged_duplicate)
        pending = sum(1 for s in results if s.status in [SubmissionStatus.SUBMITTED, SubmissionStatus.UNDER_REVIEW])

        valid = sum(1 for s in results if s.quality_score >= 80.0)
        invalid = sum(1 for s in results if s.quality_score < 50.0)
        incomplete = sum(1 for s in results if not s.mobile or not s.voter_card_number)

        avg_quality = round(sum(s.quality_score for s in results) / total, 2)
        dup_pct = round((duplicates / total) * 100, 2)
        app_pct = round((approved / total) * 100, 2)
        rej_pct = round((rejected / total) * 100, 2)

        return DataQualityStatsOut(
            total_records=total,
            valid_records=valid,
            invalid_records=invalid,
            duplicate_records=duplicates,
            incomplete_records=incomplete,
            approved_records=approved,
            pending_records=pending,
            rejected_records=rejected,
            data_quality_percentage=avg_quality,
            duplicate_percentage=dup_pct,
            approval_percentage=app_pct,
            rejection_percentage=rej_pct,
        )

    def _evaluate_quality(self, s: DataSubmission) -> DataQualityCheck:
        issues = []
        score = 100.0

        # Validate Mobile (E.164 or 10-15 digits)
        is_valid_mobile = True
        if s.mobile:
            mobile_clean = re.sub(r"[\s\-\(\)\+]", "", s.mobile)
            if not (10 <= len(mobile_clean) <= 15 and mobile_clean.isdigit()):
                is_valid_mobile = False
                issues.append("Invalid mobile number format")
                score -= 20.0
        else:
            issues.append("Missing mobile number")
            score -= 10.0

        # Validate Email
        is_valid_email = True
        if s.email:
            email_pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
            if not re.match(email_pattern, s.email):
                is_valid_email = False
                issues.append("Invalid email address format")
                score -= 15.0

        # Validate Voter Card Number
        is_valid_voter_card = True
        if s.voter_card_number:
            if len(s.voter_card_number) < 5 or len(s.voter_card_number) > 20:
                is_valid_voter_card = False
                issues.append("Voter card ID length abnormal")
                score -= 15.0
        else:
            issues.append("Missing voter card number")
            score -= 10.0

        # Required fields check
        has_required = bool(s.citizen_name and (s.mobile or s.voter_card_number))
        if not has_required:
            score -= 25.0
            issues.append("Missing critical identification details")

        score = max(0.0, min(100.0, score))

        return DataQualityCheck(
            is_valid_mobile=is_valid_mobile,
            is_valid_email=is_valid_email,
            is_valid_voter_card=is_valid_voter_card,
            has_required_fields=has_required,
            is_area_booth_mismatch=False,
            is_suspicious_repeated=False,
            quality_percentage=score,
            validation_issues_json=json.dumps(issues),
        )

    def _to_submission_out(self, s: DataSubmission) -> DataSubmissionOut:
        return DataSubmissionOut(
            id=s.id,
            organization_id=s.organization_id,
            election_id=s.election_id,
            volunteer_id=s.volunteer_id,
            volunteer_name=s.volunteer.full_name if s.volunteer else None,
            constituency_id=s.constituency_id,
            ward_id=s.ward_id,
            booth_id=s.booth_id,
            area_id=s.area_id,
            voter_id=s.voter_id,
            citizen_name=s.citizen_name,
            mobile=s.mobile,
            email=s.email,
            voter_card_number=s.voter_card_number,
            date_of_birth=s.date_of_birth,
            gender=s.gender,
            address_line=s.address_line,
            ward_no=s.ward_no,
            booth_no=s.booth_no,
            preferred_party_candidate=s.preferred_party_candidate,
            issues_concerns=s.issues_concerns,
            custom_fields_json=s.custom_fields_json,
            status=s.status,
            quality_score=s.quality_score,
            is_flagged_duplicate=s.is_flagged_duplicate,
            submission_channel=s.submission_channel,
            reviewed_by=s.reviewed_by,
            reviewed_at=s.reviewed_at,
            review_remarks=s.review_remarks,
            rejection_reason=s.rejection_reason,
            created_at=s.created_at,
            quality_check=s.quality_check,
        )
