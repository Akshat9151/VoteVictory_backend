from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_permissions
from app.core.permissions import PermissionCode
from app.models.user import User
from app.schemas.common import APIResponse
from app.schemas.import_job import ImportConfirmRequest, ImportPreviewResponse, ImportReportResponse
from app.services.import_service import BulkImportService

router = APIRouter(prefix="/imports", tags=["Bulk Import System"])


@router.post("/upload", response_model=APIResponse[ImportPreviewResponse])
async def upload_voters_file(
    request: Request,
    election_id: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(require_permissions(PermissionCode.VOTER_IMPORT.value)),
    db: AsyncSession = Depends(get_db)
):
    service = BulkImportService(db)
    preview = await service.process_upload_and_preview(request, election_id, file, current_user)
    return APIResponse(
        success=True,
        message="Spreadsheet parsed and validation preview generated.",
        data=preview
    )


@router.post("/confirm", response_model=APIResponse[ImportReportResponse])
async def confirm_import(
    request: Request,
    confirm_in: ImportConfirmRequest,
    current_user: User = Depends(require_permissions(PermissionCode.VOTER_IMPORT.value)),
    db: AsyncSession = Depends(get_db)
):
    service = BulkImportService(db)
    report = await service.confirm_bulk_import(request, confirm_in, current_user)
    return APIResponse(
        success=True,
        message=f"Successfully imported {report.successfully_imported} voter records.",
        data=report
    )
