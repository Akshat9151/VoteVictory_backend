from typing import List, Optional, Set, Tuple

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit_log
from app.core.exceptions import (
    AppException,
    DuplicateResourceException,
    InvalidStateTransitionException,
    PermissionDeniedException,
    ResourceNotFoundException,
)
from app.models.candidate import Candidate, CandidateStatus
from app.models.election import Election, ElectionSetting, ElectionStatus, Position
from app.models.user import User
from app.repositories.election_repo import ElectionRepository
from app.schemas.common import PaginationMeta
from app.schemas.election import ElectionCreate, ElectionSettingUpdate, ElectionUpdate

# Allowed State Transition Map
ALLOWED_TRANSITIONS: dict[ElectionStatus, Set[ElectionStatus]] = {
    ElectionStatus.DRAFT: {ElectionStatus.SCHEDULED, ElectionStatus.CANCELLED},
    ElectionStatus.SCHEDULED: {ElectionStatus.UPCOMING, ElectionStatus.LIVE, ElectionStatus.CANCELLED, ElectionStatus.DRAFT},
    ElectionStatus.UPCOMING: {ElectionStatus.LIVE, ElectionStatus.CANCELLED, ElectionStatus.PAUSED},
    ElectionStatus.LIVE: {ElectionStatus.PAUSED, ElectionStatus.CLOSED, ElectionStatus.CANCELLED},
    ElectionStatus.PAUSED: {ElectionStatus.LIVE, ElectionStatus.CLOSED, ElectionStatus.CANCELLED},
    ElectionStatus.CLOSED: {ElectionStatus.COUNTING, ElectionStatus.ARCHIVED},
    ElectionStatus.COUNTING: {ElectionStatus.RESULT_PUBLISHED, ElectionStatus.CLOSED},
    ElectionStatus.RESULT_PUBLISHED: {ElectionStatus.ARCHIVED},
    ElectionStatus.ARCHIVED: set(),
    ElectionStatus.CANCELLED: {ElectionStatus.DRAFT},
}


class ElectionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.election_repo = ElectionRepository(db)

    async def create_election(
        self,
        request: Request,
        election_in: ElectionCreate,
        current_user: User
    ) -> Election:
        org_id = election_in.organization_id or current_user.organization_id
        if not current_user.is_superuser and org_id != current_user.organization_id:
            raise PermissionDeniedException(message="Cannot create election in another organization.")

        # Check unique slug within org
        existing = await self.election_repo.get_by_slug(org_id, election_in.slug)
        if existing:
            raise DuplicateResourceException("Election", "slug", election_in.slug)

        election = Election(
            organization_id=org_id,
            title=election_in.title.strip(),
            slug=election_in.slug.lower().strip(),
            description=election_in.description,
            election_type=election_in.election_type,
            timezone=election_in.timezone,
            start_datetime=election_in.start_datetime,
            end_datetime=election_in.end_datetime,
            visibility=election_in.visibility,
            status=ElectionStatus.DRAFT,
            created_by=current_user.id
        )
        election = await self.election_repo.create(election)

        # Create settings
        settings_in = election_in.settings
        setting = ElectionSetting(
            election_id=election.id,
            allow_electronic_voting=settings_in.allow_electronic_voting if settings_in else True,
            require_voter_mfa=settings_in.require_voter_mfa if settings_in else False,
            require_photo_id=settings_in.require_photo_id if settings_in else False,
            allow_abstain=settings_in.allow_abstain if settings_in else True,
            result_publication_policy=settings_in.result_publication_policy if settings_in else "MANUAL_APPROVAL",
            notification_rules_json=settings_in.notification_rules_json if settings_in else None
        )
        self.db.add(setting)
        await self.db.flush()

        await record_audit_log(
            self.db,
            request,
            action="election.create",
            resource_type="election",
            resource_id=election.id,
            organization_id=org_id,
            current_user=current_user,
            new_state={"title": election.title, "status": election.status.value}
        )

        return await self.election_repo.get_by_id_loaded(election.id)

    async def get_election(self, election_id: str, current_user: User) -> Election:
        election = await self.election_repo.get_by_id_loaded(election_id)
        if not election:
            raise ResourceNotFoundException("Election", election_id)

        if not current_user.is_superuser and election.organization_id != current_user.organization_id:
            raise PermissionDeniedException(message="Cross-tenant access violation.")

        return election

    async def list_elections(
        self,
        current_user: User,
        org_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        status: Optional[ElectionStatus] = None
    ) -> Tuple[List[Election], PaginationMeta]:
        filters = {}
        if not current_user.is_superuser:
            filters["organization_id"] = current_user.organization_id
        elif org_id:
            filters["organization_id"] = org_id

        if status:
            filters["status"] = status

        return await self.election_repo.list_paginated(
            page=page,
            page_size=page_size,
            filters=filters,
            search_query=search,
            search_fields=["title", "slug", "description"]
        )

    async def update_election(
        self,
        request: Request,
        election_id: str,
        election_in: ElectionUpdate,
        current_user: User
    ) -> Election:
        election = await self.get_election(election_id, current_user)

        if election.status in (ElectionStatus.LIVE, ElectionStatus.COUNTING, ElectionStatus.RESULT_PUBLISHED, ElectionStatus.ARCHIVED):
            raise AppException(
                code="ELECTION_LOCKED",
                message=f"Cannot edit structural details of election in '{election.status.value}' state."
            )

        prev_state = {"title": election.title, "description": election.description}

        if election_in.title is not None:
            election.title = election_in.title.strip()
        if election_in.description is not None:
            election.description = election_in.description
        if election_in.election_type is not None:
            election.election_type = election_in.election_type
        if election_in.timezone is not None:
            election.timezone = election_in.timezone
        if election_in.start_datetime is not None:
            election.start_datetime = election_in.start_datetime
        if election_in.end_datetime is not None:
            election.end_datetime = election_in.end_datetime
        if election_in.visibility is not None:
            election.visibility = election_in.visibility

        updated = await self.election_repo.update(election)

        await record_audit_log(
            self.db,
            request,
            action="election.update",
            resource_type="election",
            resource_id=election.id,
            organization_id=election.organization_id,
            current_user=current_user,
            prev_state=prev_state,
            new_state={"title": updated.title}
        )
        return updated

    async def transition_lifecycle(
        self,
        request: Request,
        election_id: str,
        target_status: ElectionStatus,
        current_user: User,
        reason: Optional[str] = None
    ) -> Election:
        election = await self.get_election(election_id, current_user)
        current_status = election.status

        # Validate transition rule
        allowed = ALLOWED_TRANSITIONS.get(current_status, set())
        if target_status not in allowed:
            raise InvalidStateTransitionException(
                current_status=current_status.value,
                target_status=target_status.value,
                entity_name="Election"
            )

        # Extra validation before LIVE
        if target_status == ElectionStatus.LIVE:
            # Must have at least 1 position
            pos_stmt = select(Position).where(Position.election_id == election_id, Position.is_active == True)
            positions = (await self.db.execute(pos_stmt)).scalars().all()
            if not positions:
                raise AppException(
                    code="ELECTION_VALIDATION_FAILED",
                    message="Election cannot go LIVE without at least one active position."
                )

            # Must have approved candidates
            cand_stmt = select(Candidate).where(Candidate.election_id == election_id, Candidate.status == CandidateStatus.APPROVED)
            candidates = (await self.db.execute(cand_stmt)).scalars().all()
            if not candidates:
                raise AppException(
                    code="ELECTION_VALIDATION_FAILED",
                    message="Election cannot go LIVE without at least one APPROVED candidate."
                )

        prev_status = election.status
        election.status = target_status
        updated = await self.election_repo.update(election)

        await record_audit_log(
            self.db,
            request,
            action=f"election.transition.{target_status.value.lower()}",
            resource_type="election",
            resource_id=election.id,
            organization_id=election.organization_id,
            current_user=current_user,
            prev_state={"status": prev_status.value},
            new_state={"status": target_status.value, "reason": reason}
        )
        return updated

    async def update_settings(
        self,
        request: Request,
        election_id: str,
        settings_in: ElectionSettingUpdate,
        current_user: User
    ) -> ElectionSetting:
        election = await self.get_election(election_id, current_user)
        setting = election.settings
        if not setting:
            setting = ElectionSetting(election_id=election_id)
            self.db.add(setting)

        setting.allow_electronic_voting = settings_in.allow_electronic_voting
        setting.require_voter_mfa = settings_in.require_voter_mfa
        setting.require_photo_id = settings_in.require_photo_id
        setting.allow_abstain = settings_in.allow_abstain
        setting.result_publication_policy = settings_in.result_publication_policy
        if settings_in.notification_rules_json is not None:
            setting.notification_rules_json = settings_in.notification_rules_json

        await self.db.flush()
        await self.db.refresh(setting)

        await record_audit_log(
            self.db,
            request,
            action="election.settings.update",
            resource_type="election_setting",
            resource_id=setting.id,
            organization_id=election.organization_id,
            current_user=current_user,
            new_state={"allow_electronic_voting": setting.allow_electronic_voting}
        )
        return setting
