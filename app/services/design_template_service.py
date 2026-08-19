import uuid
from typing import List, Optional

from fastapi import HTTPException, Request, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.design_template import DesignTemplate
from app.models.user import User
from app.schemas.design_template import DesignTemplateCreate, DesignTemplateUpdate


class DesignTemplateService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_templates(
        self,
        organization_id: Optional[str] = None,
        category: Optional[str] = None,
        election_type: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> List[DesignTemplate]:
        stmt = select(DesignTemplate)
        if organization_id:
            stmt = stmt.where(
                (DesignTemplate.organization_id == organization_id)
                | (DesignTemplate.organization_id == None)
            )
        if category:
            stmt = stmt.where(DesignTemplate.category == category)
        if election_type:
            stmt = stmt.where(DesignTemplate.election_type == election_type)
        if is_active is not None:
            stmt = stmt.where(DesignTemplate.is_active == is_active)

        stmt = stmt.order_by(DesignTemplate.display_order, desc(DesignTemplate.created_at))
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_template(self, template_id: str) -> DesignTemplate:
        stmt = select(DesignTemplate).where(DesignTemplate.id == template_id)
        result = await self.db.execute(stmt)
        template = result.scalars().first()
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Design template '{template_id}' not found.",
            )
        return template

    async def create_template(
        self,
        request: Request,
        template_in: DesignTemplateCreate,
        current_user: Optional[User] = None,
    ) -> DesignTemplate:
        org_id = current_user.organization_id if current_user else None
        template = DesignTemplate(
            id=str(uuid.uuid4()),
            organization_id=org_id,
            name=template_in.name,
            election_type=template_in.election_type,
            category=template_in.category,
            format_name=template_in.format_name,
            format_dims=template_in.format_dims,
            layout_json=template_in.layout_json,
            thumbnail_url=template_in.thumbnail_url,
            is_active=template_in.is_active,
            display_order=template_in.display_order,
        )
        self.db.add(template)
        await self.db.commit()
        await self.db.refresh(template)
        return template

    async def update_template(
        self,
        request: Request,
        template_id: str,
        update_in: DesignTemplateUpdate,
        current_user: Optional[User] = None,
    ) -> DesignTemplate:
        template = await self.get_template(template_id)
        update_data = update_in.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(template, key, value)
        await self.db.commit()
        await self.db.refresh(template)
        return template

    async def delete_template(self, template_id: str, current_user: Optional[User] = None) -> bool:
        template = await self.get_template(template_id)
        await self.db.delete(template)
        await self.db.commit()
        return True
