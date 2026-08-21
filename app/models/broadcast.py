import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
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


class BroadcastGroup(Base, TimestampMixin):
    """Immutable recipient group and its saved broadcast draft."""
    __tablename__ = "broadcast_groups"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f"bg_{uuid.uuid4().hex[:16]}")
    organization_id: Mapped[str] = mapped_column(String(64), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    filter_criteria_snapshot: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_by: Mapped[str] = mapped_column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    message_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="DRAFT", nullable=False, index=True)
    excluded_no_contact: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    organization = relationship("Organization")
    creator = relationship("User")
    members = relationship("BroadcastGroupMember", back_populates="group", cascade="all, delete-orphan")
    logs = relationship("BroadcastLog", back_populates="group", cascade="all, delete-orphan")


class BroadcastGroupMember(Base, TimestampMixin):
    """Recipient snapshot with routing fixed when the group is created."""
    __tablename__ = "broadcast_group_members"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f"bgm_{uuid.uuid4().hex[:16]}")
    group_id: Mapped[str] = mapped_column(String(64), ForeignKey("broadcast_groups.id", ondelete="CASCADE"), nullable=False, index=True)
    voter_id: Mapped[str] = mapped_column(String(64), ForeignKey("voters.id", ondelete="CASCADE"), nullable=False, index=True)
    mobile: Mapped[str] = mapped_column(String(50), nullable=False)
    contact_method: Mapped[str] = mapped_column(String(16), nullable=False)
    voter_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    ward: Mapped[str] = mapped_column(String(100), nullable=False, default="")

    group = relationship("BroadcastGroup", back_populates="members")
    voter = relationship("Voter")


class BroadcastLog(Base, TimestampMixin):
    """One persisted provider attempt per group member."""
    __tablename__ = "broadcast_logs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f"bl_{uuid.uuid4().hex[:16]}")
    group_id: Mapped[str] = mapped_column(String(64), ForeignKey("broadcast_groups.id", ondelete="CASCADE"), nullable=False, index=True)
    voter_id: Mapped[str] = mapped_column(String(64), ForeignKey("voters.id", ondelete="SET NULL"), nullable=True, index=True)
    mobile: Mapped[str] = mapped_column(String(50), nullable=False)
    channel_used: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="failed")
    provider_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_at: Mapped[str | None] = mapped_column(String(64), nullable=True)

    group = relationship("BroadcastGroup", back_populates="logs")
    voter = relationship("Voter")
