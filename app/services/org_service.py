from typing import List, Optional, Tuple

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit_log
from app.core.exceptions import DuplicateResourceException, PermissionDeniedException, ResourceNotFoundException
from app.models.organization import Organization, OrganizationStatus
from app.models.user import User
from app.repositories.base import BaseRepository
from app.schemas.common import PaginationMeta
from app.schemas.organization import OrganizationCreate, OrganizationUpdate


class OrgService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.org_repo = BaseRepository(Organization, db)

    async def create_organization(self, request: Request, org_in: OrganizationCreate, current_user: User) -> Organization:
        # Check unique slug
        stmt = select(Organization).where(Organization.slug == org_in.slug.lower().strip())
        res = await self.db.execute(stmt)
        if res.scalars().first():
            raise DuplicateResourceException("Organization", "slug", org_in.slug)

        org = Organization(
            name=org_in.name.strip(),
            slug=org_in.slug.lower().strip(),
            contact_email=org_in.contact_email,
            contact_phone=org_in.contact_phone,
            address=org_in.address,
            settings_json=org_in.settings_json,
            status=OrganizationStatus.ACTIVE,
            created_by=current_user.id
        )
        org = await self.org_repo.create(org)

        await record_audit_log(
            self.db,
            request,
            action="organization.create",
            resource_type="organization",
            resource_id=org.id,
            current_user=current_user,
            new_state={"name": org.name, "slug": org.slug}
        )
        return org

    async def list_organizations(
        self,
        current_user: User,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None
    ) -> Tuple[List[Organization], PaginationMeta]:
        filters = {}
        if not current_user.is_superuser:
            filters["id"] = current_user.organization_id

        return await self.org_repo.list_paginated(
            page=page,
            page_size=page_size,
            filters=filters,
            search_query=search,
            search_fields=["name", "slug", "contact_email"]
        )

    async def get_organization(self, org_id: str, current_user: User) -> Organization:
        if not current_user.is_superuser and current_user.organization_id != org_id:
            raise PermissionDeniedException(message="Cross-tenant access violation.")

        org = await self.org_repo.get_by_id(org_id)
        if not org:
            raise ResourceNotFoundException("Organization", org_id)
        return org

    async def update_organization(
        self,
        request: Request,
        org_id: str,
        org_in: OrganizationUpdate,
        current_user: User
    ) -> Organization:
        org = await self.get_organization(org_id, current_user)
        prev_state = {"name": org.name, "status": org.status.value}

        if org_in.name is not None:
            org.name = org_in.name.strip()
        if org_in.contact_email is not None:
            org.contact_email = org_in.contact_email
        if org_in.contact_phone is not None:
            org.contact_phone = org_in.contact_phone
        if org_in.address is not None:
            org.address = org_in.address
        if org_in.settings_json is not None:
            org.settings_json = org_in.settings_json
        if org_in.status is not None and current_user.is_superuser:
            org.status = org_in.status

        updated = await self.org_repo.update(org)

        await record_audit_log(
            self.db,
            request,
            action="organization.update",
            resource_type="organization",
            resource_id=org.id,
            current_user=current_user,
            prev_state=prev_state,
            new_state={"name": org.name, "status": org.status.value}
        )
        return updated
