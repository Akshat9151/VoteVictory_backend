from typing import Optional
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import require_permissions
from app.core.permissions import PermissionCode
from app.models.election import Election, ElectionStatus
from app.models.user import User
from app.schemas.common import APIResponse, PaginatedResponse
from app.schemas.election import (
    ElectionCreate,
    ElectionResponse,
    ElectionSettingResponse,
    ElectionSettingUpdate,
    ElectionUpdate,
    LifecycleTransitionRequest,
)
from app.services.election_service import ElectionService

router = APIRouter(prefix="/elections", tags=["Election Management"])


from sqlalchemy import inspect

def serialize_election(election: Election) -> ElectionResponse:
    settings_data = None
    insp = inspect(election)
    if "settings" in insp.dict and election.settings:
        settings_data = ElectionSettingResponse(
            id=election.settings.id,
            election_id=election.id,
            allow_electronic_voting=election.settings.allow_electronic_voting,
            require_voter_mfa=election.settings.require_voter_mfa,
            require_photo_id=election.settings.require_photo_id,
            allow_abstain=election.settings.allow_abstain,
            result_publication_policy=election.settings.result_publication_policy,
            notification_rules_json=election.settings.notification_rules_json
        )

    return ElectionResponse(
        id=election.id,
        organization_id=election.organization_id,
        title=election.title,
        slug=election.slug,
        description=election.description,
        election_type=election.election_type,
        timezone=election.timezone,
        start_datetime=election.start_datetime,
        end_datetime=election.end_datetime,
        status=election.status,
        visibility=election.visibility,
        created_by=election.created_by,
        settings=settings_data,
        created_at=election.created_at,
        updated_at=election.updated_at
    )


@router.get("/", response_model=APIResponse[PaginatedResponse[ElectionResponse]])
async def list_elections(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    status: Optional[ElectionStatus] = None,
    org_id: Optional[str] = None,
    current_user: User = Depends(require_permissions(PermissionCode.ELECTION_VIEW.value)),
    db: AsyncSession = Depends(get_db)
):
    service = ElectionService(db)
    elections, pagination = await service.list_elections(
        current_user=current_user,
        org_id=org_id,
        page=page,
        page_size=page_size,
        search=search,
        status=status
    )
    items = [serialize_election(e) for e in elections]
    return APIResponse(data=PaginatedResponse(items=items, pagination=pagination))


@router.post("/", response_model=APIResponse[ElectionResponse])
async def create_election(
    request: Request,
    election_in: ElectionCreate,
    current_user: User = Depends(require_permissions(PermissionCode.ELECTION_CREATE.value)),
    db: AsyncSession = Depends(get_db)
):
    service = ElectionService(db)
    election = await service.create_election(request, election_in, current_user)
    return APIResponse(
        success=True,
        message="Election draft created.",
        data=serialize_election(election)
    )


@router.get("/{election_id}", response_model=APIResponse[ElectionResponse])
async def get_election(
    election_id: str,
    current_user: User = Depends(require_permissions(PermissionCode.ELECTION_VIEW.value)),
    db: AsyncSession = Depends(get_db)
):
    service = ElectionService(db)
    election = await service.get_election(election_id, current_user)
    return APIResponse(data=serialize_election(election))


@router.put("/{election_id}", response_model=APIResponse[ElectionResponse])
async def update_election(
    request: Request,
    election_id: str,
    election_in: ElectionUpdate,
    current_user: User = Depends(require_permissions(PermissionCode.ELECTION_UPDATE.value)),
    db: AsyncSession = Depends(get_db)
):
    service = ElectionService(db)
    election = await service.update_election(request, election_id, election_in, current_user)
    return APIResponse(
        success=True,
        message="Election details updated.",
        data=serialize_election(election)
    )


@router.post("/{election_id}/transition", response_model=APIResponse[ElectionResponse])
async def transition_election_lifecycle(
    request: Request,
    election_id: str,
    transition_in: LifecycleTransitionRequest,
    current_user: User = Depends(require_permissions(PermissionCode.ELECTION_UPDATE.value)),
    db: AsyncSession = Depends(get_db)
):
    service = ElectionService(db)
    election = await service.transition_lifecycle(
        request=request,
        election_id=election_id,
        target_status=transition_in.target_status,
        current_user=current_user,
        reason=transition_in.reason
    )
    return APIResponse(
        success=True,
        message=f"Election transitioned to {election.status.value}.",
        data=serialize_election(election)
    )


@router.put("/{election_id}/settings", response_model=APIResponse[ElectionSettingResponse])
async def update_election_settings(
    request: Request,
    election_id: str,
    settings_in: ElectionSettingUpdate,
    current_user: User = Depends(require_permissions(PermissionCode.ELECTION_UPDATE.value)),
    db: AsyncSession = Depends(get_db)
):
    service = ElectionService(db)
    setting = await service.update_settings(request, election_id, settings_in, current_user)
    return APIResponse(
        success=True,
        message="Election settings configured.",
        data=ElectionSettingResponse.model_validate(setting)
    )
