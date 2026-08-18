import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class PlanTier(str, enum.Enum):
    BASIC = "basic"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "Active"
    EXPIRING = "Expiring"
    EXPIRED = "Expired"


class PaymentGateway(str, enum.Enum):
    RAZORPAY = "Razorpay"
    STRIPE = "Stripe"
    CASHFREE = "Cashfree"
    PAYU = "PayU"


class InvoiceStatus(str, enum.Enum):
    PAID = "Paid"
    PENDING = "Pending"
    FAILED = "Failed"


class CampaignSubscription(Base):
    __tablename__ = "campaign_subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    plan_id = Column(Enum(PlanTier), default=PlanTier.PROFESSIONAL, nullable=False)
    plan_name = Column(String(100), default="Professional Plan", nullable=False)
    status = Column(Enum(SubscriptionStatus), default=SubscriptionStatus.ACTIVE, nullable=False)
    start_date = Column(String(50), nullable=False)
    expiry_date = Column(String(50), nullable=False)
    auto_renew = Column(Boolean, default=True)
    active_candidates = Column(Integer, default=5)
    active_volunteers = Column(Integer, default=50)
    whatsapp_credits = Column(Integer, default=10000)
    sms_credits = Column(Integer, default=2500)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    organization = relationship("Organization")
    user = relationship("User")


class SubscriptionInvoice(Base):
    __tablename__ = "subscription_invoices"

    id = Column(String(100), primary_key=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True)
    date = Column(String(50), nullable=False)
    plan_name = Column(String(150), nullable=False)
    amount = Column(Integer, nullable=False)
    status = Column(Enum(InvoiceStatus), default=InvoiceStatus.PAID, nullable=False)
    gateway = Column(Enum(PaymentGateway), default=PaymentGateway.RAZORPAY, nullable=False)
    transaction_id = Column(String(150), nullable=False)
    pdf_url = Column(String(500), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    organization = relationship("Organization")
