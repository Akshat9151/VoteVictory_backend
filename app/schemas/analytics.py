from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class TimeSeriesPoint(BaseModel):
    timestamp: str # e.g. "2026-08-18" or "10:00"
    label: str
    value: int
    target: Optional[int] = None


class PerformanceDataPoint(BaseModel):
    id: str
    name: str
    target: int
    collected: int
    approved: int
    rejected: int
    duplicate: int
    achievement_percentage: float


class AnalyticsChartsResponse(BaseModel):
    daily_collection_trend: List[TimeSeriesPoint] = []
    weekly_collection_trend: List[TimeSeriesPoint] = []
    monthly_collection_trend: List[TimeSeriesPoint] = []
    volunteer_performance: List[PerformanceDataPoint] = []
    area_performance: List[PerformanceDataPoint] = []
    booth_performance: List[PerformanceDataPoint] = []
    data_quality_distribution: Dict[str, int] = {} # valid, invalid, duplicate, incomplete, rejected
    voter_verification_funnel: Dict[str, int] = {} # registered, verified, checked_in, voted
    communication_delivery_rates: Dict[str, Dict[str, int]] = {} # per-channel: queued, sent, delivered, failed
    election_turnout_by_station: List[Dict[str, Any]] = []
