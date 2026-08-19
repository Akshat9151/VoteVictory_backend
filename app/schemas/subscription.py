from datetime import datetime
from typing import List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.subscription import InvoiceStatus, PaymentGateway, PlanTier, SubscriptionStatus


class SubscriptionPlanOut(BaseModel):
    id: PlanTier
    name: str
    priceMonthly: int
    priceAnnual: int
    tagline: str
    features: List[str]
    candidateLimit: Union[int, str]
    volunteerLimit: Union[int, str]
    isPopular: Optional[bool] = False
    badge: Optional[str] = None


class CurrentSubscriptionOut(BaseModel):
    planId: PlanTier
    planName: str
    status: SubscriptionStatus
    startDate: str
    expiryDate: str
    autoRenew: bool
    activeCandidates: int
    activeVolunteers: int
    whatsappCredits: int
    smsCredits: int


class UpgradeSubscriptionRequest(BaseModel):
    planId: PlanTier
    gateway: PaymentGateway = PaymentGateway.RAZORPAY


class InvoiceOut(BaseModel):
    id: str
    date: str
    planName: str
    amount: int
    status: InvoiceStatus
    gateway: PaymentGateway
    transactionId: str
    pdfUrl: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
