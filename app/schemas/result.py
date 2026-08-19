from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from app.models.result import ResultStatus


class CandidateResultItem(BaseModel):
    candidate_id: str
    candidate_name: str
    party_name: Optional[str] = None
    vote_count: int
    vote_percentage: float
    rank: int


class PositionResultResponse(BaseModel):
    position_id: str
    position_title: str
    total_votes: int
    candidates: List[CandidateResultItem] = []


ResultResponse = PositionResultResponse


class ElectionResultSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    election_id: str
    election_title: str
    status: ResultStatus
    total_eligible_voters: int
    total_checked_in: int
    total_votes_cast: int
    turnout_percentage: float
    results_by_position: List[PositionResultResponse] = []
    counted_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    published_at: Optional[datetime] = None


ResultSummaryResponse = ElectionResultSummaryResponse


class ResultPublishRequest(BaseModel):
    election_id: str
    notes: Optional[str] = None


ResultCertificationRequest = ResultPublishRequest


class ResultTallyRequest(BaseModel):
    election_id: str
