import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class VolunteerVoter(Base, TimestampMixin):
    """Ground canvassing and slip distribution tracker for volunteers."""
    __tablename__ = "volunteer_voters"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f"V-02-{uuid.uuid4().hex[:4].upper()}")
    organization_id: Mapped[str] = mapped_column(String(64), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    mobile: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    house: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="Pending", nullable=False)
    slipHanded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    organization = relationship("Organization")
