import time
from datetime import datetime
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit_log
from app.core.config import settings
from app.core.exceptions import ValidationException
from app.models.expense import Expense
from app.models.user import User
from app.repositories.expense_repo import ExpenseRepository
from app.schemas.expense import BudgetSummary, ExpenseCreate, ExpenseResponse


class ExpenseService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ExpenseRepository(db)

    def _to_response(self, e: Expense) -> ExpenseResponse:
        date_val = e.date or datetime.now().strftime("%d %b %Y")
        created_val = e.created_at.isoformat() if hasattr(e, "created_at") and e.created_at else date_val
        receipt = getattr(e, "receiptUrl", None) or getattr(e, "receipt_url", None)
        note_val = e.note or ""
        return ExpenseResponse(
            id=e.id,
            organization_id=e.organization_id,
            election_id=getattr(e, "election_id", None) or e.organization_id,
            title=getattr(e, "title", None) or note_val[:50] or e.category,
            category=e.category,
            amount=e.amount,
            date=date_val,
            expense_date=date_val,
            note=note_val,
            notes=note_val,
            mode=e.mode or "UPI / Online",
            user=e.user or "Admin",
            vendor_name=getattr(e, "vendor_name", None),
            receiptUrl=receipt,
            receipt_url=receipt,
            created_at=created_val,
            updated_at=created_val,
        )

    async def get_expenses(self, organization_id: Optional[str] = None) -> List[ExpenseResponse]:
        expenses = await self.repo.list_all(organization_id=organization_id)
        return [self._to_response(e) for e in expenses]

    async def add_expense(
        self,
        data: ExpenseCreate,
        organization_id: str,
        user: Optional[User] = None,
        ip_address: Optional[str] = None,
    ) -> ExpenseResponse:
        if data.amount <= 0:
            raise ValidationException("Expense amount must be greater than zero.")

        # 1. Enforce EC Statutory Budget Limit (₹1,50,000)
        current_total = await self.repo.get_total_spent(organization_id=organization_id)
        projected_total = current_total + data.amount
        budget_limit = settings.STATUTORY_BUDGET_LIMIT

        if projected_total > budget_limit:
            remaining = max(0.0, budget_limit - current_total)
            raise ValidationException(
                f"Statutory Budget Violation: Adding ₹{data.amount:,.2f} exceeds the Election Commission statutory "
                f"expenditure ceiling of ₹{budget_limit:,.2f}. Current total spent: ₹{current_total:,.2f}, Remaining: ₹{remaining:,.2f}."
            )

        expense_id = f"exp_{int(time.time() * 1000)}"
        date_str = data.date or data.expense_date or datetime.now().strftime("%d %b %Y")
        user_name = data.user or (user.name if user and hasattr(user, "name") and user.name else "Admin")
        receipt_str = data.receiptUrl or data.receipt_url
        note_str = data.note or data.notes or data.title or ""

        expense = Expense(
            id=expense_id,
            organization_id=organization_id,
            category=data.category,
            amount=data.amount,
            date=date_str,
            note=note_str,
            mode=data.mode or "UPI / Online",
            user=user_name,
            receiptUrl=receipt_str,
        )
        await self.repo.create(expense)

        await record_audit_log(
            db=self.db,
            action="EXPENSE_ADD",
            resource_type="expense",
            resource_id=expense.id,
            organization_id=organization_id,
            current_user=user,
            details={
                "message": f"Added expense ₹{expense.amount:,.2f} for '{expense.category}' (Mode: {expense.mode}). New total: ₹{projected_total:,.2f}",
                "ip_address": ip_address,
            },
        )
        await self.db.commit()

        return self._to_response(expense)

    async def get_budget_summary(self, organization_id: Optional[str] = None) -> BudgetSummary:
        budget_limit = settings.STATUTORY_BUDGET_LIMIT
        total_spent = await self.repo.get_total_spent(organization_id=organization_id)
        expenses = await self.repo.list_all(organization_id=organization_id)
        expense_count = len(expenses)

        remaining = max(0.0, budget_limit - total_spent)
        utilized_percent = round((total_spent / budget_limit) * 100) if budget_limit > 0 else 0

        return BudgetSummary(
            budgetLimit=budget_limit,
            totalSpent=total_spent,
            remaining=remaining,
            utilizedPercent=utilized_percent,
            budget_limit=budget_limit,
            total_spent=total_spent,
            utilized_percent=float(utilized_percent),
            expense_count=expense_count,
            expenseCount=expense_count,
        )
