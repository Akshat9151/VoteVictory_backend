from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_permissions
from app.core.permissions import PermissionCode
from app.models.data_collection import DuplicateResolutionStatus, SubmissionStatus
from app.models.user import User
from app.schemas.common import APIResponse, PaginatedResponse
from app.schemas.data_collection import (
    BulkReviewRequest,
    DataDuplicateOut,
    DataQualityStatsOut,
    DataReviewRequest,
    DataSubmissionCreate,
    DataSubmissionOut,
    DuplicateResolveRequest,
)
from app.services.data_collection_service import DataCollectionService
from app.services.duplicate_detection_service import DuplicateDetectionService

router = APIRouter(prefix="/data", tags=["Field Data Collection & Review Center"])


@router.post("/submit", response_model=APIResponse[DataSubmissionOut])
async def submit_field_data(
    request: Request,
    submission_in: DataSubmissionCreate,
    current_user: User = Depends(require_permissions(PermissionCode.DATA_SUBMIT.value)),
    db: AsyncSession = Depends(get_db),
):
    service = DataCollectionService(db)
    submission = await service.submit_field_data(request, submission_in, current_user)
    return APIResponse(
        success=True,
        message="Field data submitted successfully and analyzed for quality.",
        data=submission,
    )


@router.get("/submissions", response_model=APIResponse[PaginatedResponse[DataSubmissionOut]])
async def list_submissions(
    election_id: Optional[str] = None,
    volunteer_id: Optional[str] = None,
    booth_id: Optional[str] = None,
    area_id: Optional[str] = None,
    status: Optional[SubmissionStatus] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(require_permissions(PermissionCode.DATA_VIEW.value)),
    db: AsyncSession = Depends(get_db),
):
    service = DataCollectionService(db)
    skip = (page - 1) * page_size
    items, total = await service.list_submissions(
        organization_id=current_user.organization_id,
        election_id=election_id,
        volunteer_id=volunteer_id,
        booth_id=booth_id,
        area_id=area_id,
        status=status,
        search=search,
        skip=skip,
        limit=page_size,
    )
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1
    return APIResponse(
        data=PaginatedResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
    )


@router.get("/submissions/{submission_id}", response_model=APIResponse[DataSubmissionOut])
async def get_submission(
    submission_id: str,
    current_user: User = Depends(require_permissions(PermissionCode.DATA_VIEW.value)),
    db: AsyncSession = Depends(get_db),
):
    service = DataCollectionService(db)
    sub = await service.get_submission(submission_id)
    return APIResponse(data=sub)


@router.post("/submissions/{submission_id}/review", response_model=APIResponse[DataSubmissionOut])
async def review_submission(
    request: Request,
    submission_id: str,
    review_in: DataReviewRequest,
    current_user: User = Depends(require_permissions(PermissionCode.DATA_REVIEW.value)),
    db: AsyncSession = Depends(get_db),
):
    service = DataCollectionService(db)
    updated = await service.review_submission(request, submission_id, review_in, current_user)
    return APIResponse(
        success=True,
        message=f"Submission status updated to {updated.status}.",
        data=updated,
    )


@router.post("/submissions/bulk-review", response_model=APIResponse[Dict[str, Any]])
async def bulk_review_submissions(
    request: Request,
    bulk_in: BulkReviewRequest,
    current_user: User = Depends(require_permissions(PermissionCode.DATA_REVIEW.value)),
    db: AsyncSession = Depends(get_db),
):
    service = DataCollectionService(db)
    res = await service.bulk_review_submissions(request, bulk_in, current_user)
    return APIResponse(
        success=True,
        message=f"Successfully updated {res.get('processed_count')} records.",
        data=res,
    )


@router.get("/duplicates", response_model=APIResponse[PaginatedResponse[DataDuplicateOut]])
async def list_duplicates(
    resolution_status: Optional[DuplicateResolutionStatus] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(require_permissions(PermissionCode.DATA_REVIEW.value)),
    db: AsyncSession = Depends(get_db),
):
    dup_service = DuplicateDetectionService(db)
    skip = (page - 1) * page_size
    items, total = await dup_service.list_duplicates(
        organization_id=current_user.organization_id,
        resolution_status=resolution_status,
        skip=skip,
        limit=page_size,
    )
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1
    return APIResponse(
        data=PaginatedResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
    )


@router.post("/duplicates/resolve", response_model=APIResponse[DataDuplicateOut])
async def resolve_duplicate(
    request: Request,
    resolve_in: DuplicateResolveRequest,
    current_user: User = Depends(require_permissions(PermissionCode.DATA_REVIEW.value)),
    db: AsyncSession = Depends(get_db),
):
    dup_service = DuplicateDetectionService(db)
    resolved = await dup_service.resolve_duplicate(request, resolve_in, current_user)
    return APIResponse(
        success=True,
        message=f"Duplicate marked as {resolve_in.action}.",
        data=resolved,
    )


@router.get("/quality/stats", response_model=APIResponse[DataQualityStatsOut])
async def get_data_quality_stats(
    current_user: User = Depends(require_permissions(PermissionCode.DATA_VIEW.value)),
    db: AsyncSession = Depends(get_db),
):
    service = DataCollectionService(db)
    stats = await service.get_quality_statistics(current_user.organization_id)
    return APIResponse(data=stats)
