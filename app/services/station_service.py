from typing import List, Optional, Tuple

from fastapi import Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit_log
from app.core.exceptions import ResourceNotFoundException
from app.models.polling_station import PollingStation, VolunteerAssignment
from app.models.user import User
from app.models.voter import Voter, VoterCheckin
from app.repositories.base import BaseRepository
from app.schemas.common import PaginationMeta
from app.schemas.polling_station import PollingStationCreate, PollingStationResponse, PollingStationUpdate


class PollingStationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.station_repo = BaseRepository(PollingStation, db)

    async def create_station(self, request: Request, station_in: PollingStationCreate, current_user: User) -> PollingStation:
        station = PollingStation(
            election_id=station_in.election_id,
            constituency_id=station_in.constituency_id,
            name=station_in.name.strip(),
            code=station_in.code.strip().upper(),
            address=station_in.address.strip(),
            latitude=station_in.latitude,
            longitude=station_in.longitude,
            capacity=station_in.capacity,
            operating_hours=station_in.operating_hours,
            status=station_in.status
        )
        station = await self.station_repo.create(station)

        await record_audit_log(
            self.db,
            request,
            action="station.create",
            resource_type="polling_station",
            resource_id=station.id,
            current_user=current_user,
            new_state={"name": station.name, "code": station.code}
        )
        return station

    async def list_stations(
        self,
        election_id: str,
        page: int = 1,
        page_size: int = 50,
        search: Optional[str] = None
    ) -> Tuple[List[PollingStation], PaginationMeta]:
        filters = {"election_id": election_id}
        return await self.station_repo.list_paginated(
            page=page,
            page_size=page_size,
            filters=filters,
            search_query=search,
            search_fields=["name", "code", "address"]
        )

    async def get_station_details(self, station_id: str) -> PollingStationResponse:
        station = await self.station_repo.get_by_id(station_id)
        if not station:
            raise ResourceNotFoundException("PollingStation", station_id)

        # Query counts
        vol_count = (await self.db.execute(
            select(func.count(VolunteerAssignment.id)).where(VolunteerAssignment.polling_station_id == station_id, VolunteerAssignment.is_active == True)
        )).scalar_one() or 0

        voter_count = (await self.db.execute(
            select(func.count(Voter.id)).where(Voter.polling_station_id == station_id)
        )).scalar_one() or 0

        checkin_count = (await self.db.execute(
            select(func.count(VoterCheckin.id)).where(VoterCheckin.polling_station_id == station_id)
        )).scalar_one() or 0

        return PollingStationResponse(
            id=station.id,
            election_id=station.election_id,
            constituency_id=station.constituency_id,
            name=station.name,
            code=station.code,
            address=station.address,
            latitude=station.latitude,
            longitude=station.longitude,
            capacity=station.capacity,
            operating_hours=station.operating_hours,
            status=station.status,
            assigned_volunteers_count=vol_count,
            total_registered_voters=voter_count,
            checked_in_voters=checkin_count,
            created_at=station.created_at
        )

    async def update_station(
        self,
        request: Request,
        station_id: str,
        station_in: PollingStationUpdate,
        current_user: User
    ) -> PollingStation:
        station = await self.station_repo.get_by_id(station_id)
        if not station:
            raise ResourceNotFoundException("PollingStation", station_id)

        if station_in.name is not None:
            station.name = station_in.name.strip()
        if station_in.code is not None:
            station.code = station_in.code.strip().upper()
        if station_in.address is not None:
            station.address = station_in.address.strip()
        if station_in.latitude is not None:
            station.latitude = station_in.latitude
        if station_in.longitude is not None:
            station.longitude = station_in.longitude
        if station_in.capacity is not None:
            station.capacity = station_in.capacity
        if station_in.operating_hours is not None:
            station.operating_hours = station_in.operating_hours
        if station_in.status is not None:
            station.status = station_in.status
        if station_in.constituency_id is not None:
            station.constituency_id = station_in.constituency_id

        updated = await self.station_repo.update(station)

        await record_audit_log(
            self.db,
            request,
            action="station.update",
            resource_type="polling_station",
            resource_id=station.id,
            current_user=current_user,
            new_state={"name": updated.name}
        )
        return updated
