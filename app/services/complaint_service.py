import random
from datetime import datetime
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit_log
from app.core.exceptions import NotFoundException
from app.models.complaint import Complaint
from app.models.user import User
from app.repositories.complaint_repo import ComplaintRepository
from app.schemas.complaint import ComplaintCreate, ComplaintResponse, ComplaintStatusUpdate


class ComplaintService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ComplaintRepository(db)

    def _to_response(self, c: Complaint) -> ComplaintResponse:
        c_name = c.name or "Voter"
        c_desc = c.desc or ""
        c_ward = c.ward or "Ward 01"
        created_str = c.created_at.isoformat() if hasattr(c, "created_at") and c.created_at else c.date
        return ComplaintResponse(
            id=c.id,
            organization_id=c.organization_id,
            election_id=getattr(c, "election_id", None) or c.organization_id,
            name=c_name,
            title=c_desc[:50] or c_name,
            ward=c_ward,
            ward_name=c_ward,
            category=c.category,
            desc=c_desc,
            description=c_desc,
            reported_by_name=c_name,
            date=c.date,
            status=c.status,
            created_at=created_str,
            updated_at=created_str,
        )

    async def get_complaints(self, organization_id: Optional[str] = None) -> List[ComplaintResponse]:
        complaints = await self.repo.list_all(organization_id=organization_id)
        if not complaints and organization_id:
            complaints = await self.repo.list_all(organization_id=None)
        return [self._to_response(c) for c in complaints]

    async def add_complaint(
        self,
        data: ComplaintCreate,
        organization_id: str,
        user: Optional[User] = None,
        ip_address: Optional[str] = None,
    ) -> ComplaintResponse:
        complaint_id = f"GR-{random.randint(100, 999)}"
        date_str = datetime.now().strftime("%d %b %Y")

        c_name = data.name or data.reported_by_name or data.title or "Voter"
        c_ward = data.ward or data.ward_name or "Ward 01"
        c_desc = data.desc or data.description or data.title or "Grievance logged"
        c_category = data.category or "INFRASTRUCTURE"

        complaint = Complaint(
            id=complaint_id,
            organization_id=organization_id,
            name=c_name,
            ward=c_ward,
            category=c_category,
            desc=c_desc,
            date=date_str,
            status=data.status or "Open",
        )
        await self.repo.create(complaint)
        await record_audit_log(
            db=self.db,
            action="COMPLAINT_CREATE",
            resource_type="complaint",
            resource_id=complaint.id,
            organization_id=organization_id,
            current_user=user,
            details={
                "message": f"Filed complaint {complaint.id} ({complaint.category}): {complaint.desc[:60]}",
                "ip_address": ip_address,
            },
        )
        await self.db.commit()

        return self._to_response(complaint)

    async def update_status(
        self,
        id: str,
        data: ComplaintStatusUpdate,
        organization_id: Optional[str] = None,
        user: Optional[User] = None,
        ip_address: Optional[str] = None,
    ) -> ComplaintResponse:
        complaint = await self.repo.get_by_id(id=id, organization_id=organization_id)
        if not complaint:
            complaint = await self.repo.get_by_id(id=id)
        if not complaint:
            raise NotFoundException(f"Complaint with ID '{id}' not found.")

        old_status = complaint.status
        complaint.status = data.status

        await self.repo.update(complaint)
        await record_audit_log(
            db=self.db,
            action="COMPLAINT_STATUS_UPDATE",
            resource_type="complaint",
            resource_id=complaint.id,
            organization_id=complaint.organization_id,
            current_user=user,
            details={
                "message": f"Changed complaint status from '{old_status}' to '{data.status}'",
                "ip_address": ip_address,
            },
        )
        await self.db.commit()

        return self._to_response(complaint)
