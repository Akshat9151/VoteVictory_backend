from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.common import APIResponse
from app.schemas.voting import (
    BallotGenerateResponse,
    VoteReceiptResponse,
    VoteSubmissionRequest,
    VotingAuthRequest,
)
from app.services.voting_service import VotingEngineService

router = APIRouter(prefix="/voting", tags=["Electronic Voting Engine"])


@router.post("/auth-ballot", response_model=APIResponse[BallotGenerateResponse])
async def authenticate_voter_and_generate_ballot(
    request: Request,
    auth_in: VotingAuthRequest,
    db: AsyncSession = Depends(get_db)
):
    service = VotingEngineService(db)
    ballot_data = await service.authenticate_and_generate_ballot(request, auth_in)
    return APIResponse(
        success=True,
        message="Voter authenticated. Electronic ballot generated.",
        data=ballot_data
    )


@router.post("/cast", response_model=APIResponse[VoteReceiptResponse])
async def cast_vote(
    request: Request,
    vote_in: VoteSubmissionRequest,
    voter_id: str = Query(..., description="Voter unique ID"),
    db: AsyncSession = Depends(get_db)
):
    service = VotingEngineService(db)
    receipt = await service.cast_ballot(request, vote_in, voter_id)
    return APIResponse(
        success=True,
        message=receipt.message,
        data=receipt
    )
