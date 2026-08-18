from datetime import datetime
from typing import List, Optional
from fastapi import Request
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit_log
from app.core.exceptions import ResourceNotFoundException
from app.models.banner import Banner, BannerStatus
from app.models.election import Election
from app.models.organization import Organization
from app.models.user import User
from app.repositories.base import BaseRepository
from app.schemas.banner import BannerCreate, BannerOut, BannerUpdate


class BannerService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = BaseRepository(Banner, db)

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

    async def create_banner(
        self,
        request: Request,
        banner_in: BannerCreate,
        current_user: User,
    ) -> BannerOut:
        org_id = await self._resolve_org_id(current_user, banner_in.election_id)
        banner = Banner(
            organization_id=org_id,
            election_id=banner_in.election_id,
            campaign_id=banner_in.campaign_id,
            title=banner_in.title,
            description=banner_in.description,
            image_url=banner_in.image_url,
            cta_text=banner_in.cta_text,
            cta_link=banner_in.cta_link,
            start_date=banner_in.start_date,
            end_date=banner_in.end_date,
            display_order=banner_in.display_order,
            status=banner_in.status,
        )
        banner = await self.repo.create(banner)
        await record_audit_log(
            self.db,
            request,
            action="banner.create",
            resource_type="banner",
            resource_id=banner.id,
            current_user=current_user,
            new_state={"title": banner.title, "status": str(banner.status)},
        )
        return BannerOut.model_validate(banner)

    async def list_banners(
        self,
        organization_id: Optional[str] = None,
        election_id: Optional[str] = None,
        status: Optional[BannerStatus] = None,
    ) -> List[BannerOut]:
        stmt = select(Banner)
        if organization_id:
            stmt = stmt.where(Banner.organization_id == organization_id)
        if election_id:
            stmt = stmt.where(Banner.election_id == election_id)
        if status:
            stmt = stmt.where(Banner.status == status)

        stmt = stmt.order_by(Banner.display_order, desc(Banner.created_at))
        results = (await self.db.execute(stmt)).scalars().all()
        return [BannerOut.model_validate(b) for b in results]

    async def update_banner(
        self,
        request: Request,
        banner_id: str,
        update_in: BannerUpdate,
        current_user: User,
    ) -> BannerOut:
        banner = await self.repo.get_by_id(banner_id)
        if not banner:
            raise ResourceNotFoundException("Banner", banner_id)

        if update_in.title is not None:
            banner.title = update_in.title
        if update_in.description is not None:
            banner.description = update_in.description
        if update_in.image_url is not None:
            banner.image_url = update_in.image_url
        if update_in.cta_text is not None:
            banner.cta_text = update_in.cta_text
        if update_in.cta_link is not None:
            banner.cta_link = update_in.cta_link
        if update_in.start_date is not None:
            banner.start_date = update_in.start_date
        if update_in.end_date is not None:
            banner.end_date = update_in.end_date
        if update_in.display_order is not None:
            banner.display_order = update_in.display_order
        if update_in.status is not None:
            banner.status = update_in.status

        updated = await self.repo.update(banner)
        await record_audit_log(
            self.db,
            request,
            action="banner.update",
            resource_type="banner",
            resource_id=banner.id,
            current_user=current_user,
            new_state={"status": str(updated.status)},
        )
        return BannerOut.model_validate(updated)
