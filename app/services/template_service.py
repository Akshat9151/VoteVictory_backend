import re
from typing import List, Optional

from fastapi import Request
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit_log
from app.core.exceptions import ResourceNotFoundException
from app.models.notification import NotificationChannel, NotificationTemplate
from app.models.organization import Organization
from app.models.user import User
from app.repositories.base import BaseRepository
from app.schemas.notification import (
    TemplateCreate,
    TemplateResponse,
    TemplateUpdate,
    TemplateVariablePreviewRequest,
    TemplateVariablePreviewResponse,
)


class TemplateService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = BaseRepository(NotificationTemplate, db)

    async def _resolve_org_id(self, current_user: User) -> Optional[str]:
        if current_user.organization_id:
            return current_user.organization_id
        stmt = select(Organization).limit(1)
        org = (await self.db.execute(stmt)).scalars().first()
        return org.id if org else None

    async def create_template(
        self,
        request: Request,
        template_in: TemplateCreate,
        current_user: User,
    ) -> TemplateResponse:
        org_id = await self._resolve_org_id(current_user)
        template = NotificationTemplate(
            organization_id=org_id,
            name=template_in.name,
            code=template_in.code,
            channel=template_in.channel,
            template_type=template_in.template_type,
            external_template_id=template_in.external_template_id,
            content_template=template_in.content_template,
            variables_schema_json=template_in.variables_schema_json,
            is_approved=True,
        )
        template = await self.repo.create(template)
        await record_audit_log(
            self.db,
            request,
            action="template.create",
            resource_type="notification_template",
            resource_id=template.id,
            current_user=current_user,
            new_state={"code": template.code, "channel": str(template.channel)},
        )
        return TemplateResponse.model_validate(template)

    async def list_templates(
        self,
        organization_id: Optional[str] = None,
        channel: Optional[NotificationChannel] = None,
    ) -> List[TemplateResponse]:
        stmt = select(NotificationTemplate)
        if organization_id:
            stmt = stmt.where(
                (NotificationTemplate.organization_id == organization_id)
                | (NotificationTemplate.organization_id.is_(None))
            )
        if channel:
            stmt = stmt.where(NotificationTemplate.channel == channel)

        stmt = stmt.order_by(desc(NotificationTemplate.created_at))
        results = (await self.db.execute(stmt)).scalars().all()
        return [TemplateResponse.model_validate(t) for t in results]

    async def update_template(
        self,
        request: Request,
        template_id: str,
        update_in: TemplateUpdate,
        current_user: User,
    ) -> TemplateResponse:
        template = await self.repo.get_by_id(template_id)
        if not template:
            raise ResourceNotFoundException("NotificationTemplate", template_id)

        if update_in.name:
            template.name = update_in.name
        if update_in.content_template:
            template.content_template = update_in.content_template
        if update_in.external_template_id is not None:
            template.external_template_id = update_in.external_template_id
        if update_in.is_approved is not None:
            template.is_approved = update_in.is_approved

        updated = await self.repo.update(template)
        await record_audit_log(
            self.db,
            request,
            action="template.update",
            resource_type="notification_template",
            resource_id=template.id,
            current_user=current_user,
            new_state={"name": updated.name},
        )
        return TemplateResponse.model_validate(updated)

    async def preview_template(
        self,
        preview_in: TemplateVariablePreviewRequest,
    ) -> TemplateVariablePreviewResponse:
        template = await self.repo.get_by_id(preview_in.template_id)
        if not template:
            raise ResourceNotFoundException("NotificationTemplate", preview_in.template_id)

        content = template.content_template
        # Find all variables like {{name}}
        variables = re.findall(r"\{\{([a-zA-Z0-9_]+)\}\}", content)
        missing_vars = []
        rendered = content

        for var in set(variables):
            if var in preview_in.sample_data:
                rendered = rendered.replace(f"{{{{{var}}}}}", str(preview_in.sample_data[var]))
            else:
                missing_vars.append(var)

        is_valid = len(missing_vars) == 0

        return TemplateVariablePreviewResponse(
            template_id=template.id,
            original_template=content,
            rendered_preview=rendered,
            missing_variables=missing_vars,
            is_valid=is_valid,
        )
