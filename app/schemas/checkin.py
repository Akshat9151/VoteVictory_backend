from datetime import datetime

from pydantic import BaseModel, ConfigDict


class VoterCheckinRequest(BaseModel):
    voter_id: str
    election_id: str
    polling_station_id: str
    checkin_method: str = "VOLUNTEER_SCAN" # VOLUNTEER_SCAN, STATION_APP, ONLINE_AUTH


class VoterCheckinResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    voter_id: str
    election_id: str
    polling_station_id: str
    checked_in_by: str
    checkin_method: str
    checkin_time: datetime
    message: str = "Voter successfully verified and checked in."
