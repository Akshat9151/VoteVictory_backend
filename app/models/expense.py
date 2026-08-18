import uuid
from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin


class Expense(Base, TimestampMixin):
    """Campaign election expense record subject to Election Commission ₹1,50,000 statutory limit."""
    __tablename__ = "expenses"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f"exp_{uuid.uuid4().hex[:8]}")
    organization_id: Mapped[str] = mapped_column(String(64), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(150), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    date: Mapped[str] = mapped_column(String(64), nullable=False)
    note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    mode: Mapped[str] = mapped_column(String(50), default="UPI / Online", nullable=False)  # UPI / Online, Cash Voucher, Bank Transfer, Cheque
    user: Mapped[str] = mapped_column(String(150), nullable=False)
    receiptUrl: Mapped[str] = mapped_column(String(500), nullable=True)

    # Relationships
    organization = relationship("Organization")
