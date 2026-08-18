from typing import List, Optional

from fastapi import Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit_log
from app.core.exceptions import ResourceNotFoundException
from app.models.area import Area, Booth, BoothStatus, MapStatus, Ward
from app.models.data_collection import DataSubmission, SubmissionStatus
from app.models.election import Constituency, Election
from app.models.organization import Organization
from app.models.user import User
from app.models.volunteer import VolunteerProfile
from app.repositories.base import BaseRepository
from app.schemas.area import (
    AreaCreate,
    AreaOut,
    BoothCreate,
    BoothOut,
    BoothStatsOut,
    MapMetricsOut,
    WardCreate,
    WardOut,
)


class AreaBoothService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.ward_repo = BaseRepository(Ward, db)
        self.booth_repo = BaseRepository(Booth, db)
        self.area_repo = BaseRepository(Area, db)

    async def _resolve_org_id(self, current_user: User, constituency_id: Optional[str] = None) -> str:
        if current_user.organization_id:
            return current_user.organization_id
        if constituency_id:
            const = await self.db.get(Constituency, constituency_id)
            if const and const.election_id:
                elec = await self.db.get(Election, const.election_id)
                if elec:
                    return elec.organization_id
        stmt = select(Organization).limit(1)
        org = (await self.db.execute(stmt)).scalars().first()
        return org.id if org else ""

    # Ward Operations
    async def create_ward(self, request: Request, ward_in: WardCreate, current_user: User) -> WardOut:
        org_id = await self._resolve_org_id(current_user, ward_in.constituency_id)
        ward = Ward(
            organization_id=org_id,
            constituency_id=ward_in.constituency_id,
            ward_number=ward_in.ward_number,
            name=ward_in.name,
            description=ward_in.description,
        )
        ward = await self.ward_repo.create(ward)
        await record_audit_log(
            self.db,
            request,
            action="ward.create",
            resource_type="ward",
            resource_id=ward.id,
            current_user=current_user,
            new_state={"ward_number": ward.ward_number, "name": ward.name},
        )
        return WardOut.model_validate(ward)

    async def list_wards(self, organization_id: Optional[str] = None, constituency_id: Optional[str] = None) -> List[WardOut]:
        stmt = select(Ward)
        if organization_id:
            stmt = stmt.where(Ward.organization_id == organization_id)
        if constituency_id:
            stmt = stmt.where(Ward.constituency_id == constituency_id)
        results = (await self.db.execute(stmt)).scalars().all()
        return [WardOut.model_validate(w) for w in results]

    # Booth Operations
    async def create_booth(self, request: Request, booth_in: BoothCreate, current_user: User) -> BoothOut:
        org_id = await self._resolve_org_id(current_user, booth_in.constituency_id)
        booth = Booth(
            organization_id=org_id,
            constituency_id=booth_in.constituency_id,
            ward_id=booth_in.ward_id,
            booth_number=booth_in.booth_number,
            name=booth_in.name,
            location_address=booth_in.location_address,
            latitude=booth_in.latitude,
            longitude=booth_in.longitude,
            target=booth_in.target,
            status=BoothStatus.ACTIVE,
        )
        booth = await self.booth_repo.create(booth)
        await record_audit_log(
            self.db,
            request,
            action="booth.create",
            resource_type="booth",
            resource_id=booth.id,
            current_user=current_user,
            new_state={"booth_number": booth.booth_number, "target": booth.target},
        )
        return self._to_booth_out(booth)

    async def list_booths(
        self,
        organization_id: Optional[str] = None,
        constituency_id: Optional[str] = None,
        ward_id: Optional[str] = None,
    ) -> List[BoothOut]:
        stmt = select(Booth)
        if organization_id:
            stmt = stmt.where(Booth.organization_id == organization_id)
        if constituency_id:
            stmt = stmt.where(Booth.constituency_id == constituency_id)
        if ward_id:
            stmt = stmt.where(Booth.ward_id == ward_id)
        results = (await self.db.execute(stmt)).scalars().all()
        return [self._to_booth_out(b) for b in results]

    async def get_booth_stats(self, booth_id: str) -> BoothStatsOut:
        booth = await self.booth_repo.get_by_id(booth_id)
        if not booth:
            raise ResourceNotFoundException("Booth", booth_id)

        # Active volunteers in booth
        vol_stmt = select(func.count()).where(
            VolunteerProfile.booth_id == booth_id,
            VolunteerProfile.status == "ACTIVE",
        )
        vol_count = (await self.db.execute(vol_stmt)).scalar_one()

        # Pending data records
        pending_stmt = select(func.count()).where(
            DataSubmission.booth_id == booth_id,
            DataSubmission.status == SubmissionStatus.SUBMITTED,
        )
        pending_count = (await self.db.execute(pending_stmt)).scalar_one()

        achieve_pct = round((booth.collected_count / booth.target * 100) if booth.target > 0 else 0.0, 2)

        return BoothStatsOut(
            booth_id=booth.id,
            booth_number=booth.booth_number,
            booth_name=booth.name,
            target=booth.target,
            collected=booth.collected_count,
            achievement_percentage=achieve_pct,
            active_volunteers_count=vol_count,
            pending_data_count=pending_count,
        )

    # Area Operations
    async def create_area(self, request: Request, area_in: AreaCreate, current_user: User) -> AreaOut:
        org_id = await self._resolve_org_id(current_user, area_in.constituency_id)
        area = Area(
            organization_id=org_id,
            constituency_id=area_in.constituency_id,
            ward_id=area_in.ward_id,
            booth_id=area_in.booth_id,
            state=area_in.state,
            district=area_in.district,
            name=area_in.name,
            code=area_in.code,
            target=area_in.target,
            map_status=MapStatus.GREY,
            boundary_geojson=area_in.boundary_geojson,
        )
        area = await self.area_repo.create(area)
        await record_audit_log(
            self.db,
            request,
            action="area.create",
            resource_type="area",
            resource_id=area.id,
            current_user=current_user,
            new_state={"name": area.name, "target": area.target},
        )
        return self._to_area_out(area)

    async def list_areas(
        self,
        organization_id: Optional[str] = None,
        constituency_id: Optional[str] = None,
        booth_id: Optional[str] = None,
    ) -> List[AreaOut]:
        stmt = select(Area)
        if organization_id:
            stmt = stmt.where(Area.organization_id == organization_id)
        if constituency_id:
            stmt = stmt.where(Area.constituency_id == constituency_id)
        if booth_id:
            stmt = stmt.where(Area.booth_id == booth_id)
        results = (await self.db.execute(stmt)).scalars().all()
        return [self._to_area_out(a) for a in results]

    async def get_map_metrics(self, organization_id: Optional[str] = None) -> List[MapMetricsOut]:
        stmt = select(Area)
        if organization_id:
            stmt = stmt.where(Area.organization_id == organization_id)
        results = (await self.db.execute(stmt)).scalars().all()

        metrics = []
        for a in results:
            achieve_pct = round((a.collected_count / a.target * 100) if a.target > 0 else 0.0, 2)
            if a.collected_count == 0:
                status = MapStatus.GREY
            elif achieve_pct >= 100.0:
                status = MapStatus.GREEN
            elif achieve_pct >= 50.0:
                status = MapStatus.YELLOW
            else:
                status = MapStatus.RED

            metrics.append(
                MapMetricsOut(
                    area_id=a.id,
                    area_name=a.name,
                    state=a.state,
                    district=a.district,
                    target=a.target,
                    collected=a.collected_count,
                    achievement_percentage=achieve_pct,
                    status=status,
                )
            )
        return metrics

    def _to_booth_out(self, b: Booth) -> BoothOut:
        achieve_pct = round((b.collected_count / b.target * 100) if b.target > 0 else 0.0, 2)
        return BoothOut(
            id=b.id,
            organization_id=b.organization_id,
            constituency_id=b.constituency_id,
            ward_id=b.ward_id,
            booth_number=b.booth_number,
            name=b.name,
            location_address=b.location_address,
            latitude=b.latitude,
            longitude=b.longitude,
            target=b.target,
            collected_count=b.collected_count,
            achievement_percentage=achieve_pct,
            status=b.status,
            created_at=b.created_at,
        )

    def _to_area_out(self, a: Area) -> AreaOut:
        achieve_pct = round((a.collected_count / a.target * 100) if a.target > 0 else 0.0, 2)
        if a.collected_count == 0:
            map_stat = MapStatus.GREY
        elif achieve_pct >= 100.0:
            map_stat = MapStatus.GREEN
        elif achieve_pct >= 50.0:
            map_stat = MapStatus.YELLOW
        else:
            map_stat = MapStatus.RED

        return AreaOut(
            id=a.id,
            organization_id=a.organization_id,
            constituency_id=a.constituency_id,
            ward_id=a.ward_id,
            booth_id=a.booth_id,
            state=a.state,
            district=a.district,
            name=a.name,
            code=a.code,
            target=a.target,
            collected_count=a.collected_count,
            achievement_percentage=achieve_pct,
            map_status=map_stat,
            boundary_geojson=a.boundary_geojson,
            created_at=a.created_at,
        )
