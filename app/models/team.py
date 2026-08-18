import uuid
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin


class TeamMember(Base, TimestampMixin):
    """Campaign team member roster."""
    __tablename__ = "team_members"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f"team_{uuid.uuid4().hex[:8]}")
    organization_id: Mapped[str] = mapped_column(String(64), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="Volunteer", nullable=False)  # Super Admin, Admin, Volunteer
    roleTitle: Mapped[str] = mapped_column(String(150), nullable=False)
    ward: Mapped[str] = mapped_column(String(150), nullable=False)
    phone: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="Active", nullable=False)  # Active, Inactive, Invited
    votersHandled: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    addedDate: Mapped[str] = mapped_column(String(64), nullable=False)

    # Relationships
    organization = relationship("Organization")


class Volunteer(Base, TimestampMixin):
    """Field volunteer with productivity metrics."""
    __tablename__ = "volunteers"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f"vol_{uuid.uuid4().hex[:8]}")
    organization_id: Mapped[str] = mapped_column(String(64), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    role: Mapped[str] = mapped_column(String(150), nullable=False)
    ward: Mapped[str] = mapped_column(String(150), nullable=False)
    phone: Mapped[str] = mapped_column(String(32), nullable=False)
    votersAdded: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    callsMade: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    slipsDistributed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="Active", nullable=False)  # Active, On-Duty, Inactive

    # Relationships
    organization = relationship("Organization")
