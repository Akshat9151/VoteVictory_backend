import random
from datetime import datetime
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_audit_event
from app.core.exceptions import NotFoundException
from app.models.complaint import Complaint
from app.models.user import User
from app.repositories.complaint_repo import ComplaintRepository
from app.schemas.complaint import ComplaintCreate, ComplaintResponse, ComplaintStatusUpdate


class ComplaintService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ComplaintRepository(db)

    async def get_complaints(self, organization_id: str) -> List[ComplaintResponse]:
        complaints = await self.repo.list_all(organization_id=organization_id)
        return [
            ComplaintResponse(
                id=c.id,
                name=c.name,
                ward=c.ward,
                category=c.category,
                desc=c.desc,
                date=c.date,
                status=c.status
            )
            for c in complaints
        ]

    async def add_complaint(
        self,
        data: ComplaintCreate,
        organization_id: str,
        user: Optional[User] = None,
        ip_address: Optional[str] = None
    ) -> ComplaintResponse:
        complaint_id = f"GR-{random.randint(100, 999)}"
        date_str = datetime.now().strftime("%d %b %Y")

        complaint = Complaint(
            id=complaint_id,
            organization_id=organization_id,
            name=data.name,
            ward=data.ward,
            category=data.category,
            desc=data.desc,
            date=date_str,
            status=data.status or "Open"
        )
        await self.repo.create(complaint)
        await log_audit_event(
            db=self.db,
            action="COMPLAINT_CREATE",
            entity_type="complaint",
            entity_id=complaint.id,
            organization_id=organization_id,
            user=user,
            details=f"Filed complaint {complaint.id} ({complaint.category}): {complaint.desc[:60]}",
            ip_address=ip_address
        )
        await self.db.commit()

        return ComplaintResponse(
            id=complaint.id,
            name=complaint.name,
            ward=complaint.ward,
            category=complaint.category,
            desc=complaint.desc,
            date=complaint.date,
            status=complaint.status
        )

    async def update_status(
        self,
        id: str,
        data: ComplaintStatusUpdate,
        organization_id: str,
        user: Optional[User] = None,
        ip_address: Optional[str] = None
    ) -> ComplaintResponse:
        complaint = await self.repo.get_by_id(id=id, organization_id=organization_id)
        if not complaint:
            raise NotFoundException(f"Complaint with ID '{id}' not found.")

        old_status = complaint.status
        complaint.status = data.status

        await log_audit_event(
            db=self.db,
            action="COMPLAINT_STATUS_UPDATE",
            entity_type="complaint",
            entity_id=complaint.id,
            organization_id=organization_id,
            user=user,
            details=f"Changed complaint status from '{old_status}' to '{data.status}'",
            ip_address=ip_address
        )
        await self.db.commit()

        return ComplaintResponse(
            id=complaint.id,
            name=complaint.name,
            ward=complaint.ward,
            category=complaint.category,
            desc=complaint.desc,
            date=complaint.date,
            status=complaint.status
        )
