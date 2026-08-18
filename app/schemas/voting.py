from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class VotingAuthRequest(BaseModel):
    voter_id_number: str = Field(..., description="Voter ID / EPIC Number")
    election_id: str
    verification_code: Optional[str] = Field(None, description="OTP or pass-code if configured")


VotingSessionInitiate = VotingAuthRequest


class BallotCandidateOption(BaseModel):
    candidate_id: str
    full_name: str
    party_name: Optional[str] = None
    party_symbol_url: Optional[str] = None
    photo_url: Optional[str] = None
    manifesto: Optional[str] = None
    display_order: int = 0


class BallotPosition(BaseModel):
    position_id: str
    title: str
    description: Optional[str] = None
    min_selections: int = 1
    max_selections: int = 1
    allow_abstain: bool = True
    candidates: List[BallotCandidateOption] = []


class BallotGenerateResponse(BaseModel):
    session_token: str
    election_id: str
    election_title: str
    expires_at: datetime
    positions: List[BallotPosition] = []


VotingSessionResponse = BallotGenerateResponse


class VoteSelection(BaseModel):
    position_id: str
    candidate_ids: List[str] = Field(..., description="List of chosen candidate IDs for this position")


class VoteSubmissionRequest(BaseModel):
    session_token: str
    election_id: str
    selections: List[VoteSelection]


CastVoteRequest = VoteSubmissionRequest


class VoteReceiptResponse(BaseModel):
    success: bool = True
    ballot_serial_hash: str
    cast_timestamp: str
    message: str = "Ballot successfully anonymized and cast in database."


CastVoteResponse = VoteReceiptResponse
BallotAuditReceipt = VoteReceiptResponse
