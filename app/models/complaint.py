import random

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Complaint(Base, TimestampMixin):
    """Voter grievance and issue tracking."""
    __tablename__ = "complaints"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f"GR-{random.randint(100, 999)}")
    organization_id: Mapped[str] = mapped_column(String(64), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    election_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("elections.id", ondelete="SET NULL"), nullable=True, index=True)
    created_by_user_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reported_by_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ward: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    desc: Mapped[str] = mapped_column(Text, nullable=False)
    date: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="Open", nullable=False)

    # Relationships
    organization = relationship("Organization")
    created_by = relationship("User")
