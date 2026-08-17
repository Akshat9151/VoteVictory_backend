from typing import List
from pydantic import BaseModel


class HourlyTurnoutItem(BaseModel):
    hour: str # e.g. "08:00", "09:00"
    voter_count: int
    cumulative_percentage: float


class StationTurnoutItem(BaseModel):
    station_id: str
    station_name: str
    registered_voters: int
    votes_cast: int
    turnout_percentage: float


class ConstituencyTurnoutItem(BaseModel):
    constituency_id: str
    constituency_name: str
    registered_voters: int
    votes_cast: int
    turnout_percentage: float


class TurnoutAnalyticsResponse(BaseModel):
    election_id: str
    total_registered_voters: int
    total_votes_cast: int
    overall_turnout_percentage: float
    hourly_trends: List[HourlyTurnoutItem] = []
    station_breakdown: List[StationTurnoutItem] = []
    constituency_breakdown: List[ConstituencyTurnoutItem] = []
