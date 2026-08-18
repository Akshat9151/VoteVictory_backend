import uuid
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin


class DeliveryLog(Base, TimestampMixin):
    """WhatsApp & SMS broadcast delivery audit records."""
    __tablename__ = "delivery_logs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f"log_{uuid.uuid4().hex[:8]}")
    organization_id: Mapped[str] = mapped_column(String(64), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    broadcast_id: Mapped[str] = mapped_column(String(64), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    ward: Mapped[str] = mapped_column(String(100), nullable=False)
    mobile: Mapped[str] = mapped_column(String(32), nullable=False)
    route: Mapped[str] = mapped_column(String(32), default="WhatsApp", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="Sending", nullable=False)
    read: Mapped[str] = mapped_column(String(64), default="Delivered ✓✓", nullable=False)
    time: Mapped[str] = mapped_column(String(32), nullable=False)

    # Relationships
    organization = relationship("Organization")
