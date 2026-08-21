import random
from datetime import datetime
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit_log
from app.core.exceptions import NotFoundException
from app.models.complaint import Complaint
from app.models.user import User
from app.repositories.complaint_repo import ComplaintRepository
from app.schemas.complaint import ComplaintCreate, ComplaintResponse, ComplaintStatusUpdate, ComplaintUpdate


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
            election_id=getattr(c, "election_id", None),
            name=c_name,
            title=c.title or c_desc[:50] or c_name,
            ward=c_ward,
            ward_name=c_ward,
            category=c.category,
            desc=c_desc,
            description=c_desc,
            reported_by_name=c_name,
            reported_by_phone=c.reported_by_phone,
            submitted_by_name=c.created_by.full_name if c.created_by else None,
            submitted_by_user_id=c.created_by_user_id,
            date=c.date,
            status=c.status,
            created_at=created_str,
            updated_at=created_str,
        )

    async def get_complaints(self, organization_id: Optional[str] = None, election_id: Optional[str] = None, created_by_user_id: Optional[str] = None) -> List[ComplaintResponse]:
        complaints = await self.repo.list_all(organization_id=organization_id, filters={"election_id": election_id, "created_by_user_id": created_by_user_id})
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
            election_id=data.election_id,
            created_by_user_id=user.id if user else None,
            name=c_name,
            title=data.title,
            reported_by_phone=data.reported_by_phone,
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

    async def update_complaint(self, id: str, data: ComplaintUpdate, organization_id: str, user: Optional[User] = None, ip_address: Optional[str] = None) -> ComplaintResponse:
        complaint = await self.repo.get_by_id(id=id, organization_id=organization_id)
        if not complaint:
            raise NotFoundException(f"Complaint with ID '{id}' not found.")
        if data.name is not None or data.reported_by_name is not None:
            complaint.name = data.name or data.reported_by_name or complaint.name
        if data.title is not None:
            complaint.title = data.title
        if data.reported_by_phone is not None:
            complaint.reported_by_phone = data.reported_by_phone
        if data.ward is not None or data.ward_name is not None:
            complaint.ward = data.ward or data.ward_name or complaint.ward
        if data.category is not None:
            complaint.category = data.category
        if data.desc is not None or data.description is not None or data.title is not None:
            complaint.desc = data.desc or data.description or data.title or complaint.desc
        # Status is intentionally excluded from general edits.
        await self.repo.update(complaint)
        await record_audit_log(self.db, action="COMPLAINT_UPDATE", resource_type="complaint", resource_id=complaint.id, organization_id=organization_id, current_user=user, details={"message": f"Updated complaint {complaint.id}", "ip_address": ip_address})
        await self.db.commit()
        return self._to_response(complaint)

    async def delete_complaint(self, id: str, organization_id: str, user: Optional[User] = None, ip_address: Optional[str] = None) -> bool:
        complaint = await self.repo.get_by_id(id=id, organization_id=organization_id)
        if not complaint:
            raise NotFoundException(f"Complaint with ID '{id}' not found.")
        await self.repo.delete(complaint)
        await record_audit_log(self.db, action="COMPLAINT_DELETE", resource_type="complaint", resource_id=id, organization_id=organization_id, current_user=user, details={"message": f"Deleted complaint {id}", "ip_address": ip_address})
        await self.db.commit()
        return True

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
