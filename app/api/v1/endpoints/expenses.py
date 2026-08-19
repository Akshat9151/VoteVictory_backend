from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_optional_current_user, require_roles
from app.models.organization import Organization
from app.models.user import User
from app.schemas.common import APIResponse, PaginatedResponse, PaginationMeta
from app.schemas.expense import BudgetSummary, ExpenseCreate, ExpenseResponse
from app.services.expense_service import ExpenseService

router = APIRouter(prefix="/expenses", tags=["Expenses & Budget (EC Compliance)"])


async def get_default_org_id(db: AsyncSession) -> str:
    org = (await db.execute(select(Organization).limit(1))).scalars().first()
    return org.id if org else "default_org"


@router.get("", response_model=List[ExpenseResponse])
@router.get("/", response_model=List[ExpenseResponse])
async def get_expenses(
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List campaign election expenditure records."""
    org_id = current_user.organization_id if current_user else await get_default_org_id(db)
    service = ExpenseService(db)
    return await service.get_expenses(organization_id=org_id)


@router.get("/election/{election_id}", response_model=APIResponse[PaginatedResponse[ExpenseResponse]])
async def list_election_expenses(
    election_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List election expenses with pagination for the election dashboard."""
    org_id = current_user.organization_id if current_user else await get_default_org_id(db)
    service = ExpenseService(db)
    items = await service.get_expenses(organization_id=org_id)
    total_items = len(items)
    pagination = PaginationMeta(
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=max(1, (total_items + page_size - 1) // page_size),
        has_next=False,
        has_prev=False,
    )
    return APIResponse(
        success=True,
        message="Expenses retrieved successfully.",
        data=PaginatedResponse(items=items, pagination=pagination, total=total_items),
    )


@router.get("/election/{election_id}/summary", response_model=APIResponse[BudgetSummary])
async def get_election_budget_summary(
    election_id: str,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve election budget summary and statutory ceiling utilization for an election."""
    org_id = current_user.organization_id if current_user else await get_default_org_id(db)
    service = ExpenseService(db)
    summary = await service.get_budget_summary(organization_id=org_id)
    return APIResponse(
        success=True,
        message="Budget summary calculated.",
        data=summary,
    )


@router.post("", response_model=ExpenseResponse, dependencies=[Depends(require_roles(["superadmin", "admin"]))])
@router.post("/", response_model=ExpenseResponse, dependencies=[Depends(require_roles(["superadmin", "admin"]))])
async def add_expense(
    request: Request,
    expense: ExpenseCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Log an election expense.
    Enforces statutory expenditure ceiling of ₹1,50,000 as mandated by Election Commission guidelines.
    """
    service = ExpenseService(db)
    client_ip = request.client.host if request.client else None
    return await service.add_expense(
        data=expense,
        organization_id=current_user.organization_id,
        user=current_user,
        ip_address=client_ip,
    )


@router.post("/election/{election_id}", response_model=APIResponse[ExpenseResponse], dependencies=[Depends(require_roles(["superadmin", "admin"]))])
async def add_election_expense(
    election_id: str,
    request: Request,
    expense: ExpenseCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Log an expense for a specific election campaign."""
    expense.election_id = election_id
    service = ExpenseService(db)
    client_ip = request.client.host if request.client else None
    created = await service.add_expense(
        data=expense,
        organization_id=current_user.organization_id,
        user=current_user,
        ip_address=client_ip,
    )
    return APIResponse(
        success=True,
        message="Expense logged successfully.",
        data=created,
    )


@router.get("/budget-summary", response_model=BudgetSummary)
async def get_budget_summary(
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve election budget summary and statutory ceiling utilization."""
    org_id = current_user.organization_id if current_user else await get_default_org_id(db)
    service = ExpenseService(db)
    return await service.get_budget_summary(organization_id=org_id)
