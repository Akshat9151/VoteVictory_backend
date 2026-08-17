from typing import Optional
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import require_permissions, require_super_admin
from app.core.permissions import PermissionCode
from app.models.user import User
from app.schemas.common import APIResponse, PaginatedResponse
from app.schemas.organization import OrganizationCreate, OrganizationResponse, OrganizationUpdate
from app.services.org_service import OrgService

router = APIRouter(prefix="/organizations", tags=["Organization Management"])


@router.get("/", response_model=APIResponse[PaginatedResponse[OrganizationResponse]])
async def list_organizations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    current_user: User = Depends(require_permissions(PermissionCode.ORGANIZATION_VIEW.value)),
    db: AsyncSession = Depends(get_db)
):
    service = OrgService(db)
    orgs, pagination = await service.list_organizations(current_user, page, page_size, search)
    items = [OrganizationResponse.model_validate(o) for o in orgs]
    return APIResponse(data=PaginatedResponse(items=items, pagination=pagination))


@router.post("/", response_model=APIResponse[OrganizationResponse])
async def create_organization(
    request: Request,
    org_in: OrganizationCreate,
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db)
):
    service = OrgService(db)
    org = await service.create_organization(request, org_in, current_user)
    return APIResponse(
        success=True,
        message="Organization successfully created.",
        data=OrganizationResponse.model_validate(org)
    )


@router.get("/{org_id}", response_model=APIResponse[OrganizationResponse])
async def get_organization(
    org_id: str,
    current_user: User = Depends(require_permissions(PermissionCode.ORGANIZATION_VIEW.value)),
    db: AsyncSession = Depends(get_db)
):
    service = OrgService(db)
    org = await service.get_organization(org_id, current_user)
    return APIResponse(data=OrganizationResponse.model_validate(org))


@router.put("/{org_id}", response_model=APIResponse[OrganizationResponse])
async def update_organization(
    request: Request,
    org_id: str,
    org_in: OrganizationUpdate,
    current_user: User = Depends(require_permissions(PermissionCode.ORGANIZATION_UPDATE.value)),
    db: AsyncSession = Depends(get_db)
):
    service = OrgService(db)
    org = await service.update_organization(request, org_id, org_in, current_user)
    return APIResponse(
        success=True,
        message="Organization settings updated.",
        data=OrganizationResponse.model_validate(org)
    )
