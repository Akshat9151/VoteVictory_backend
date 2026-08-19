from typing import List, Optional

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_optional_current_user
from app.adapters.storage_adapter import StorageAdapter
from app.models.saved_design import SavedDesign
from app.schemas.saved_design import SavedDesignCreate, SavedDesignResponse
from app.models.user import User
from app.schemas.common import APIResponse
from app.schemas.design_template import (
    DesignTemplateCreate,
    DesignTemplateResponse,
    DesignTemplateUpdate,
)
from app.services.design_template_service import DesignTemplateService

router = APIRouter(prefix="/design-templates", tags=["Design Studio & Campaign Creative"])


@router.get("", response_model=APIResponse[List[DesignTemplateResponse]])
@router.get("/", response_model=APIResponse[List[DesignTemplateResponse]])
async def list_design_templates(
    category: Optional[str] = Query(None),
    election_type: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve available Design Studio poster, banner, and ID card templates."""
    org_id = current_user.organization_id if current_user else None
    service = DesignTemplateService(db)
    templates = await service.list_templates(
        organization_id=org_id,
        category=category,
        election_type=election_type,
        is_active=is_active,
    )
    items = [DesignTemplateResponse.model_validate(t) for t in templates]
    return APIResponse(data=items)


@router.get("/{template_id}", response_model=APIResponse[DesignTemplateResponse])
async def get_design_template(
    template_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Fetch specific creative design template with element layout JSON."""
    service = DesignTemplateService(db)
    template = await service.get_template(template_id)
    return APIResponse(data=DesignTemplateResponse.model_validate(template))


@router.post("", response_model=APIResponse[DesignTemplateResponse], status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=APIResponse[DesignTemplateResponse], status_code=status.HTTP_201_CREATED)
async def create_design_template(
    request: Request,
    template_in: DesignTemplateCreate,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Register a new campaign poster/banner design template."""
    service = DesignTemplateService(db)
    template = await service.create_template(request, template_in, current_user)
    return APIResponse(
        success=True,
        message="Design template registered successfully.",
        data=DesignTemplateResponse.model_validate(template),
    )


@router.patch("/{template_id}", response_model=APIResponse[DesignTemplateResponse])
@router.put("/{template_id}", response_model=APIResponse[DesignTemplateResponse])
async def update_design_template(
    request: Request,
    template_id: str,
    update_in: DesignTemplateUpdate,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update design template layout, dimensions or metadata."""
    service = DesignTemplateService(db)
    template = await service.update_template(request, template_id, update_in, current_user)
    return APIResponse(
        success=True,
        message="Design template updated successfully.",
        data=DesignTemplateResponse.model_validate(template),
    )


@router.delete("/{template_id}", response_model=APIResponse[bool])
async def delete_design_template(
    template_id: str,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a custom design template."""
    service = DesignTemplateService(db)
    await service.delete_template(template_id, current_user)
    return APIResponse(success=True, message="Design template deleted successfully.", data=True)


@router.post("/upload", response_model=APIResponse[dict])
async def upload_design_asset(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    url = await StorageAdapter().save_file(file, subfolder="designs")
    return APIResponse(data={"url": url, "filename": file.filename or "asset"})


@router.post("/designs", response_model=APIResponse[SavedDesignResponse], status_code=status.HTTP_201_CREATED)
async def save_design(
    design_in: SavedDesignCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    design = SavedDesign(
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        template_id=design_in.template_id,
        election_id=design_in.election_id,
        title=design_in.title,
        form_data=design_in.form_data,
        canvas_json=design_in.canvas_json,
        preview_image_url=design_in.preview_image_url,
    )
    db.add(design)
    await db.commit()
    await db.refresh(design)
    return APIResponse(data=SavedDesignResponse.model_validate(design))


@router.get("/designs/my", response_model=APIResponse[list[SavedDesignResponse]])
async def list_my_designs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select

    result = await db.execute(
        select(SavedDesign)
        .where(SavedDesign.organization_id == current_user.organization_id, SavedDesign.user_id == current_user.id)
        .order_by(SavedDesign.created_at.desc())
    )
    return APIResponse(data=[SavedDesignResponse.model_validate(item) for item in result.scalars().all()])
