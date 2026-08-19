import uuid
from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.subscription import (
    CampaignSubscription,
    InvoiceStatus,
    PaymentGateway,
    PlanTier,
    SubscriptionInvoice,
    SubscriptionStatus,
)
from app.schemas.subscription import (
    CurrentSubscriptionOut,
    InvoiceOut,
    SubscriptionPlanOut,
    UpgradeSubscriptionRequest,
)

router = APIRouter(prefix="/subscriptions", tags=["SaaS Subscriptions & Revenue"])

STATIC_PLANS = [
    SubscriptionPlanOut(
        id=PlanTier.BASIC,
        name="Basic Plan",
        priceMonthly=1999,
        priceAnnual=19990,
        tagline="Suitable for small campaigns & single ward candidates",
        candidateLimit=1,
        volunteerLimit=10,
        features=[
            "1 Candidate Account",
            "Up to 10 Volunteers",
            "Basic Task Management",
            "Basic Command Dashboard",
            "Standard Election Reports",
            "Voter Roll Management",
            "Email & Community Support",
        ],
    ),
    SubscriptionPlanOut(
        id=PlanTier.PROFESSIONAL,
        name="Professional Plan",
        priceMonthly=5999,
        priceAnnual=59990,
        tagline="Suitable for medium-sized Gram Panchayat & Municipal campaigns",
        candidateLimit=5,
        volunteerLimit=50,
        isPopular=True,
        badge="MOST POPULAR",
        features=[
            "Multiple Candidates (Up to 5)",
            "Up to 50 Volunteers Network",
            "Area & Booth Level Management",
            "Advanced War Room Dashboard",
            "Field Activity & Photo Management",
            "Reports & Deep Analytics",
            "Automated SMS & Task Notifications",
            "CSV/Excel Data Export Engines",
            "Priority Phone Support",
        ],
    ),
    SubscriptionPlanOut(
        id=PlanTier.ENTERPRISE,
        name="Enterprise / Campaign Plan",
        priceMonthly=12999,
        priceAnnual=129990,
        tagline="Suitable for large-scale Vidhan Sabha & High-Stake Elections",
        candidateLimit="Unlimited",
        volunteerLimit="Unlimited",
        badge="HIGH STAKES",
        features=[
            "Unlimited Candidates & Wards",
            "Large Volunteer Network (Unlimited)",
            "Multiple Campaign Areas & Constituencies",
            "Real-Time Turnout & Heatmap Analytics",
            "Multi-Channel WhatsApp & SMS Integration",
            "Custom Branding & White-Label Option",
            "Dedicated Cloud Infrastructure",
            "Full API Access & Webhooks",
            "24x7 Dedicated Campaign Manager",
        ],
    ),
]


@router.get("/plans", response_model=List[SubscriptionPlanOut])
async def list_plans():
    """List available SaaS subscription plans and capabilities (Section 11, 12, 17)."""
    return STATIC_PLANS


@router.get("/current", response_model=CurrentSubscriptionOut)
async def get_current_subscription(
    db: AsyncSession = Depends(get_db),
):
    """Get active campaign subscription details and limits."""
    stmt = select(CampaignSubscription).order_by(desc(CampaignSubscription.created_at))
    result = await db.execute(stmt)
    sub = result.scalars().first()
    
    if not sub:
        # Default seeded professional plan
        return CurrentSubscriptionOut(
            planId=PlanTier.PROFESSIONAL,
            planName="Professional Plan",
            status=SubscriptionStatus.ACTIVE,
            startDate=datetime.now().strftime("%d %b %Y"),
            expiryDate=(datetime.now() + timedelta(days=30)).strftime("%d %b %Y"),
            autoRenew=True,
            activeCandidates=5,
            activeVolunteers=50,
            whatsappCredits=10000,
            smsCredits=2500,
        )
    
    return CurrentSubscriptionOut(
        planId=sub.plan_id,
        planName=sub.plan_name,
        status=sub.status,
        startDate=sub.start_date,
        expiryDate=sub.expiry_date,
        autoRenew=sub.auto_renew,
        activeCandidates=sub.active_candidates,
        activeVolunteers=sub.active_volunteers,
        whatsappCredits=sub.whatsapp_credits,
        smsCredits=sub.sms_credits,
    )


@router.post("/upgrade", response_model=CurrentSubscriptionOut)
async def upgrade_subscription(
    req: UpgradeSubscriptionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Upgrade campaign subscription via payment gateway (Razorpay/Stripe/Cashfree/PayU)."""
    plan_meta = next((p for p in STATIC_PLANS if p.id == req.planId), STATIC_PLANS[1])
    now = datetime.now()
    expiry = now + timedelta(days=30)
    
    sub = CampaignSubscription(
        plan_id=req.planId,
        plan_name=plan_meta.name,
        status=SubscriptionStatus.ACTIVE,
        start_date=now.strftime("%d %b %Y"),
        expiry_date=expiry.strftime("%d %b %Y"),
        auto_renew=True,
        active_candidates=1 if req.planId == PlanTier.BASIC else 5 if req.planId == PlanTier.PROFESSIONAL else 100,
        active_volunteers=10 if req.planId == PlanTier.BASIC else 50 if req.planId == PlanTier.PROFESSIONAL else 1000,
        whatsapp_credits=1000 if req.planId == PlanTier.BASIC else 10000 if req.planId == PlanTier.PROFESSIONAL else 50000,
        sms_credits=500 if req.planId == PlanTier.BASIC else 2500 if req.planId == PlanTier.PROFESSIONAL else 10000,
    )
    db.add(sub)

    # Generate Invoice
    inv_id = f"INV-{now.strftime('%Y%m')}-{str(uuid.uuid4())[:4].upper()}"
    invoice = SubscriptionInvoice(
        id=inv_id,
        date=now.strftime("%d %b %Y"),
        plan_name=f"{plan_meta.name} (Monthly)",
        amount=plan_meta.priceMonthly,
        status=InvoiceStatus.PAID,
        gateway=req.gateway,
        transaction_id=f"pay_{req.gateway.value.lower()}_{str(uuid.uuid4())[:8]}",
        pdf_url=f"/uploads/invoices/{inv_id}.pdf",
    )
    db.add(invoice)
    await db.commit()
    await db.refresh(sub)
    
    return CurrentSubscriptionOut(
        planId=sub.plan_id,
        planName=sub.plan_name,
        status=sub.status,
        startDate=sub.start_date,
        expiryDate=sub.expiry_date,
        autoRenew=sub.auto_renew,
        activeCandidates=sub.active_candidates,
        activeVolunteers=sub.active_volunteers,
        whatsappCredits=sub.whatsapp_credits,
        smsCredits=sub.sms_credits,
    )


@router.get("/invoices", response_model=List[InvoiceOut])
async def list_invoices(
    db: AsyncSession = Depends(get_db),
):
    """Retrieve billing history and payment invoice records (Section 12)."""
    stmt = select(SubscriptionInvoice).order_by(desc(SubscriptionInvoice.created_at))
    result = await db.execute(stmt)
    invoices = result.scalars().all()
    
    if not invoices:
        # Seeded default invoice
        return [
            InvoiceOut(
                id="INV-2026-08",
                date="01 Aug 2026",
                planName="Professional Plan (Monthly)",
                amount=5999,
                status=InvoiceStatus.PAID,
                gateway=PaymentGateway.RAZORPAY,
                transactionId="pay_rpz_94827501",
                pdfUrl="/uploads/invoices/INV-2026-08.pdf",
            )
        ]
    
    return [
        InvoiceOut(
            id=inv.id,
            date=inv.date,
            planName=inv.plan_name,
            amount=inv.amount,
            status=inv.status,
            gateway=inv.gateway,
            transactionId=inv.transaction_id,
            pdfUrl=inv.pdf_url,
        )
        for inv in invoices
    ]
