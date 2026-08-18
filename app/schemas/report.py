from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class VolunteerReportRow(BaseModel):
    volunteer_name: str
    volunteer_code: str
    area_name: Optional[str] = None
    booth_number: Optional[str] = None
    daily_target: int
    monthly_target: int
    collected_count: int
    approved_count: int
    rejected_count: int
    duplicate_count: int
    achievement_percentage: float


class DataReportRow(BaseModel):
    submission_id: str
    citizen_name: str
    mobile: Optional[str] = None
    voter_card_number: Optional[str] = None
    area_name: Optional[str] = None
    booth_no: Optional[str] = None
    volunteer_name: Optional[str] = None
    status: str
    quality_score: float
    submitted_at: datetime


class ElectionReportSummary(BaseModel):
    election_title: str
    status: str
    total_voters: int
    eligible_voters: int
    checked_in_voters: int
    total_votes_cast: int
    turnout_percentage: float
    total_stations: int
    total_candidates: int


class CampaignReportRow(BaseModel):
    campaign_name: str
    channel: str
    audience_type: str
    total_recipients: int
    sent_count: int
    delivered_count: int
    failed_count: int
    delivery_rate: float
