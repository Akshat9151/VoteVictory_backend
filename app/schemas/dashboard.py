from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class AreaCollectionSummary(BaseModel):
    area_id: str
    area_name: str
    target: int
    collected: int
    achievement_percentage: float
    map_status: str


class BoothCollectionSummary(BaseModel):
    booth_id: str
    booth_number: str
    booth_name: str
    target: int
    collected: int
    achievement_percentage: float


class VolunteerPerformanceSummary(BaseModel):
    volunteer_id: str
    volunteer_name: str
    volunteer_code: str
    collected_records: int
    approved_records: int
    achievement_percentage: float


class RecentActivityItem(BaseModel):
    id: str
    activity_type: str
    title: str
    description: str
    timestamp: str
    actor_name: str


class CampaignChannelMetric(BaseModel):
    channel: str
    sent_count: int = 0
    delivered_count: int = 0


class ElectionStatsCard(BaseModel):
    election_id: str
    title: str
    status: str
    total_voters: int = 0
    turnout_percentage: float = 0.0


class StationTurnoutSummary(BaseModel):
    station_id: str
    name: str
    code: str
    capacity: int
    checked_in_count: int


class VoterTurnoutSummary(BaseModel):
    total_eligible: int = 0
    checked_in: int = 0
    voted: int = 0
    turnout_percentage: float = 0.0


class ExecutiveOverviewResponse(BaseModel):
    total_elections: int = 0
    active_elections: int = 0
    total_voters: int = 0
    checked_in_voters: int = 0
    total_votes_cast: int = 0
    overall_turnout_percentage: float = 0.0
    total_polling_stations: int = 0
    active_polling_stations: int = 0
    total_candidates: int = 0
    approved_candidates: int = 0
    total_volunteers: int = 0
    active_volunteers: int = 0


class AdminDashboardResponse(BaseModel):
    total_volunteers: int = 0
    active_volunteers: int = 0
    total_data_collected: int = 0
    today_data_collected: int = 0
    weekly_data_collected: int = 0
    monthly_data_collected: int = 0
    approved_records: int = 0
    pending_records: int = 0
    rejected_records: int = 0
    duplicate_records: int = 0
    average_data_quality: float = 100.0
    active_campaigns: int = 0
    total_sms_sent: int = 0
    total_whatsapp_sent: int = 0
    total_email_sent: int = 0
    total_instagram_sent: int = 0
    top_performing_volunteers: List[VolunteerPerformanceSummary] = []
    area_progress: List[AreaCollectionSummary] = []
    booth_progress: List[BoothCollectionSummary] = []
    recent_activities: List[RecentActivityItem] = []


class SuperAdminDashboardResponse(BaseModel):
    total_organizations: int = 0
    active_organizations: int = 0
    total_users: int = 0
    active_elections: int = 0
    completed_elections: int = 0
    total_voters_registered: int = 0
    total_votes_processed: int = 0
    total_broadcasts_sent: int = 0
    recent_security_events: List[Dict[str, Any]] = []
    recent_audit_logs: List[Dict[str, Any]] = []


class VolunteerDashboardResponse(BaseModel):
    volunteer_name: str
    volunteer_code: str
    assigned_election_id: Optional[str] = None
    assigned_election_title: Optional[str] = None
    assigned_station_id: Optional[str] = None
    assigned_station_name: Optional[str] = None
    assigned_booth_number: Optional[str] = None
    assigned_area_name: Optional[str] = None
    task_role: str = "FIELD_VOLUNTEER"
    
    daily_target: int = 200
    daily_collection: int = 0
    achievement_percentage: float = 0.0
    remaining_target: int = 200
    
    total_submissions: int = 0
    approved_count: int = 0
    rejected_count: int = 0
    duplicate_count: int = 0
    rank_in_org: int = 1
