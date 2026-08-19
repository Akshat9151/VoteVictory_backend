from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_permissions
from app.core.permissions import PermissionCode
from app.models.user import User
from app.schemas.common import APIResponse
from app.schemas.result import ElectionResultSummaryResponse, ResultPublishRequest, ResultTallyRequest
from app.services.result_service import ResultService

router = APIRouter(prefix="/results", tags=["Result Management"])


@router.get("/election/{election_id}", response_model=APIResponse[ElectionResultSummaryResponse])
async def get_election_results(
    election_id: str,
    current_user: User = Depends(require_permissions(PermissionCode.RESULT_VIEW.value)),
    db: AsyncSession = Depends(get_db)
):
    service = ResultService(db)
    results = await service.get_results(election_id)
    return APIResponse(data=results)


@router.post("/election/{election_id}/tally", response_model=APIResponse[ElectionResultSummaryResponse])
async def tally_election_results_by_param(
    request: Request,
    election_id: str,
    current_user: User = Depends(require_permissions(PermissionCode.RESULT_COUNT.value)),
    db: AsyncSession = Depends(get_db)
):
    service = ResultService(db)
    results = await service.tally_results(request, election_id, current_user)
    return APIResponse(
        success=True,
        message="Election ballots tallied and summarized.",
        data=results
    )


@router.post("/tally", response_model=APIResponse[ElectionResultSummaryResponse])
async def tally_election_results_by_body(
    request: Request,
    tally_in: ResultTallyRequest,
    current_user: User = Depends(require_permissions(PermissionCode.RESULT_COUNT.value)),
    db: AsyncSession = Depends(get_db)
):
    service = ResultService(db)
    results = await service.tally_results(request, tally_in.election_id, current_user)
    return APIResponse(
        success=True,
        message="Election ballots tallied and summarized.",
        data=results
    )


@router.post("/publish", response_model=APIResponse[ElectionResultSummaryResponse])
async def publish_results(
    request: Request,
    pub_in: ResultPublishRequest,
    current_user: User = Depends(require_permissions(PermissionCode.RESULT_PUBLISH.value)),
    db: AsyncSession = Depends(get_db)
):
    service = ResultService(db)
    results = await service.publish_results(request, pub_in, current_user)
    return APIResponse(
        success=True,
        message="Election results approved and officially published.",
        data=results
    )
