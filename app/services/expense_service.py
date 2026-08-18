import time
from datetime import datetime
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_audit_event
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

    async def get_expenses(self, organization_id: str) -> List[ExpenseResponse]:
        expenses = await self.repo.list_all(organization_id=organization_id)
        return [
            ExpenseResponse(
                id=e.id,
                category=e.category,
                amount=e.amount,
                date=e.date,
                note=e.note,
                mode=e.mode,
                user=e.user,
                receiptUrl=e.receiptUrl
            )
            for e in expenses
        ]

    async def add_expense(
        self,
        data: ExpenseCreate,
        organization_id: str,
        user: Optional[User] = None,
        ip_address: Optional[str] = None
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
        date_str = data.date or datetime.now().strftime("%d %b %Y")
        user_name = data.user or (user.name if user else "Campaign User")

        expense = Expense(
            id=expense_id,
            organization_id=organization_id,
            category=data.category,
            amount=data.amount,
            date=date_str,
            note=data.note or "",
            mode=data.mode or "UPI / Online",
            user=user_name,
            receiptUrl=data.receiptUrl
        )
        await self.repo.create(expense)

        await log_audit_event(
            db=self.db,
            action="EXPENSE_ADD",
            entity_type="expense",
            entity_id=expense.id,
            organization_id=organization_id,
            user=user,
            details=f"Added expense ₹{expense.amount:,.2f} for '{expense.category}' (Mode: {expense.mode}). New total: ₹{projected_total:,.2f}",
            ip_address=ip_address
        )
        await self.db.commit()

        return ExpenseResponse(
            id=expense.id,
            category=expense.category,
            amount=expense.amount,
            date=expense.date,
            note=expense.note,
            mode=expense.mode,
            user=expense.user,
            receiptUrl=expense.receiptUrl
        )

    async def get_budget_summary(self, organization_id: str) -> BudgetSummary:
        budget_limit = settings.STATUTORY_BUDGET_LIMIT
        total_spent = await self.repo.get_total_spent(organization_id=organization_id)
        remaining = max(0.0, budget_limit - total_spent)
        utilized_percent = round((total_spent / budget_limit) * 100) if budget_limit > 0 else 0

        return BudgetSummary(
            budgetLimit=budget_limit,
            totalSpent=total_spent,
            remaining=remaining,
            utilizedPercent=utilized_percent
        )
