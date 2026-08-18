from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_permissions
from app.core.permissions import PermissionCode
from app.models.user import User
from app.schemas.common import APIResponse
from app.schemas.report import (
    CampaignReportRow,
    DataReportRow,
    ElectionReportSummary,
    VolunteerReportRow,
)
from app.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["Reporting & Certified Exports"])


@router.get("/volunteers", response_model=APIResponse[List[VolunteerReportRow]])
async def get_volunteer_report(
    current_user: User = Depends(require_permissions(PermissionCode.REPORT_GENERATE.value)),
    db: AsyncSession = Depends(get_db),
):
    service = ReportService(db)
    report = await service.get_volunteer_report(current_user.organization_id)
    return APIResponse(data=report)


@router.get("/volunteers/export/csv")
async def export_volunteers_csv(
    current_user: User = Depends(require_permissions(PermissionCode.REPORT_GENERATE.value)),
    db: AsyncSession = Depends(get_db),
):
    service = ReportService(db)
    report = await service.get_volunteer_report(current_user.organization_id)
    headers = [
        "Volunteer Name",
        "Volunteer Code",
        "Area ID",
        "Booth ID",
        "Daily Target",
        "Monthly Target",
        "Collected",
        "Approved",
        "Rejected",
        "Duplicate",
        "Achievement %",
    ]
    rows = [
        [
            r.volunteer_name,
            r.volunteer_code,
            r.area_name or "",
            r.booth_number or "",
            r.daily_target,
            r.monthly_target,
            r.collected_count,
            r.approved_count,
            r.rejected_count,
            r.duplicate_count,
            r.achievement_percentage,
        ]
        for r in report
    ]
    csv_data = service.export_to_csv(headers, rows)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=volunteer_report.csv"},
    )


@router.get("/data", response_model=APIResponse[List[DataReportRow]])
async def get_data_report(
    limit: int = Query(200, ge=1, le=1000),
    current_user: User = Depends(require_permissions(PermissionCode.REPORT_GENERATE.value)),
    db: AsyncSession = Depends(get_db),
):
    service = ReportService(db)
    report = await service.get_data_report(current_user.organization_id, limit)
    return APIResponse(data=report)


@router.get("/data/export/csv")
async def export_data_csv(
    limit: int = Query(500, ge=1, le=5000),
    current_user: User = Depends(require_permissions(PermissionCode.REPORT_GENERATE.value)),
    db: AsyncSession = Depends(get_db),
):
    service = ReportService(db)
    report = await service.get_data_report(current_user.organization_id, limit)
    headers = ["Submission ID", "Citizen Name", "Mobile", "Voter Card", "Booth", "Volunteer", "Status", "Quality Score", "Submitted At"]
    rows = [
        [
            r.submission_id,
            r.citizen_name,
            r.mobile or "",
            r.voter_card_number or "",
            r.booth_no or "",
            r.volunteer_name or "",
            r.status,
            r.quality_score,
            r.submitted_at.isoformat(),
        ]
        for r in report
    ]
    csv_data = service.export_to_csv(headers, rows)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=data_collection_report.csv"},
    )


@router.get("/elections/{election_id}", response_model=APIResponse[Optional[ElectionReportSummary]])
async def get_election_report(
    election_id: str,
    current_user: User = Depends(require_permissions(PermissionCode.REPORT_GENERATE.value)),
    db: AsyncSession = Depends(get_db),
):
    service = ReportService(db)
    report = await service.get_election_report(election_id)
    return APIResponse(data=report)


@router.get("/campaigns", response_model=APIResponse[List[CampaignReportRow]])
async def get_campaign_report(
    current_user: User = Depends(require_permissions(PermissionCode.REPORT_GENERATE.value)),
    db: AsyncSession = Depends(get_db),
):
    service = ReportService(db)
    report = await service.get_campaign_report(current_user.organization_id)
    return APIResponse(data=report)
