from typing import Any, Dict, List
from pydantic import BaseModel


class SuperAdminDashboardResponse(BaseModel):
    total_organizations: int
    active_organizations: int
    total_users: int
    active_elections: int
    completed_elections: int
    total_voters_registered: int
    total_votes_processed: int
    total_broadcasts_sent: int
    recent_security_events: List[Dict[str, Any]] = []
    recent_audit_logs: List[Dict[str, Any]] = []


class AdminDashboardResponse(BaseModel):
    election_id: str
    election_title: str
    election_status: str
    total_voters: int
    eligible_voters: int
    checked_in_voters: int
    votes_cast: int
    turnout_percentage: float
    total_polling_stations: int
    active_volunteers: int
    total_candidates: int
    broadcasts_dispatched: int
    pending_tasks: int


class VolunteerDashboardResponse(BaseModel):
    volunteer_name: str
    assigned_election_id: str
    assigned_election_title: str
    assigned_station_id: str
    assigned_station_name: str
    station_address: str
    task_role: str
    total_ward_voters: int
    checked_in_count: int
    voters_visited_count: int
    voters_called_count: int
