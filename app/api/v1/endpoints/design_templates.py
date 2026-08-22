from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_optional_current_user, require_permissions
from app.core.permissions import PermissionCode
from app.adapters.storage_adapter import StorageAdapter
from app.models.app_notification import AppNotification
from app.models.poster_share import PosterShare
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
poster_router = APIRouter(prefix="/posters", tags=["Poster Sharing"])


@router.get("", response_model=APIResponse[List[DesignTemplateResponse]])
@router.get("/", response_model=APIResponse[List[DesignTemplateResponse]])
async def list_design_templates(
    category: Optional[str] = Query(None),
    election_type: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve available Design Studio poster, banner, and ID card templates."""
    org_id = current_user.organization_id
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
    current_user: User = Depends(require_permissions(PermissionCode.TEMPLATE_MANAGE.value)),
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
    current_user: User = Depends(require_permissions(PermissionCode.TEMPLATE_MANAGE.value)),
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
    current_user: User = Depends(require_permissions(PermissionCode.TEMPLATE_MANAGE.value)),
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
        .where(SavedDesign.organization_id == current_user.organization_id)
        .where(SavedDesign.user_id == current_user.id if not current_user.is_superuser else True)
        .order_by(SavedDesign.created_at.desc())
    )
    return APIResponse(data=[SavedDesignResponse.model_validate(item) for item in result.scalars().all()])


@router.get("/shared-with-me", response_model=APIResponse[list[SavedDesignResponse]])
async def list_shared_designs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    shares = (await db.execute(
        select(PosterShare)
        .where(PosterShare.shared_with_user_id == current_user.id)
        .order_by(PosterShare.created_at.desc())
    )).scalars().all()
    posters = []
    for share in shares:
        poster = (await db.get(SavedDesign, share.poster_id))
        if poster and (
            current_user.is_superuser or poster.organization_id == current_user.organization_id
        ):
            posters.append(poster)
    return APIResponse(data=[SavedDesignResponse.model_validate(item) for item in posters])


@poster_router.get("/shared-with-me", response_model=APIResponse[list[SavedDesignResponse]])
async def list_shared_designs_alias(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_shared_designs(current_user=current_user, db=db)


@router.post("/designs/{design_id}/share", response_model=APIResponse[dict])
async def share_design(
    design_id: str,
    payload: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    recipient_ids = payload.get("recipient_ids") or []
    if not recipient_ids:
        raise HTTPException(status_code=400, detail="At least one recipient is required.")

    design = (await db.execute(select(SavedDesign).where(
        SavedDesign.id == design_id,
        SavedDesign.organization_id == current_user.organization_id,
    ))).scalars().first()
    if not design:
        raise HTTPException(status_code=404, detail="Saved poster not found")

    if not current_user.is_superuser and design.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You cannot share this saved poster")

    users = (await db.execute(
        select(User).where(
            User.id.in_(recipient_ids),
            ((User.organization_id == current_user.organization_id) | User.is_superuser.is_(True))
        )
    )).scalars().all()
    if not users:
        raise HTTPException(status_code=400, detail="No valid recipients found in this organization or system.")

    valid_ids = {user.id for user in users}
    if current_user.id in valid_ids:
        raise HTTPException(status_code=400, detail="You cannot share a poster with yourself.")
    invalid_ids = [user_id for user_id in recipient_ids if user_id not in valid_ids]
    if invalid_ids:
        raise HTTPException(status_code=400, detail=f"Invalid recipient(s): {', '.join(invalid_ids)}")

    existing = set((await db.execute(select(PosterShare.shared_with_user_id).where(
        PosterShare.poster_id == design_id,
        PosterShare.shared_with_user_id.in_(list(valid_ids))
    ))).scalars().all())

    created = []
    for recipient_id in sorted(valid_ids):
        if recipient_id in existing:
            continue
        share = PosterShare(
            poster_id=design_id,
            shared_by_user_id=current_user.id,
            shared_with_user_id=recipient_id,
            is_read=False,
        )
        db.add(share)
        created.append(recipient_id)
        db.add(AppNotification(
            user_id=recipient_id,
            notification_type="poster-shared",
            title="Poster Shared With You",
            message=f"{current_user.first_name} {current_user.last_name} shared a campaign poster with you.",
            link="/studio",
            related_poster_id=design_id,
            is_read=False,
        ))

    await db.commit()
    return APIResponse(success=True, message="Poster shared successfully.", data={"shared_count": len(created), "recipient_ids": created})


@poster_router.post("/{design_id}/share", response_model=APIResponse[dict])
async def share_design_alias(
    design_id: str,
    payload: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await share_design(design_id=design_id, payload=payload, current_user=current_user, db=db)


@router.delete("/designs/{design_id}", response_model=APIResponse[bool])
async def delete_saved_design(
    design_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    design = (await db.execute(select(SavedDesign).where(
        SavedDesign.id == design_id,
        SavedDesign.organization_id == current_user.organization_id,
    ))).scalars().first()
    if not design:
        raise HTTPException(status_code=404, detail="Saved poster not found")
    if not current_user.is_superuser and design.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You cannot delete this saved poster")
    await db.delete(design)
    await db.commit()
    return APIResponse(success=True, message="Saved poster deleted.", data=True)
