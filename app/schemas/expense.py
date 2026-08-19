from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ExpenseBase(BaseModel):
    category: str = "PRINTING"
    amount: float
    title: Optional[str] = None
    note: Optional[str] = ""
    notes: Optional[str] = None
    mode: Optional[str] = "UPI / Online"  # UPI / Online, Cash Voucher, Bank Transfer, Cheque
    user: Optional[str] = "Admin"
    vendor_name: Optional[str] = None
    receiptUrl: Optional[str] = None
    receipt_url: Optional[str] = None
    expense_date: Optional[str] = None


class ExpenseCreate(ExpenseBase):
    election_id: Optional[str] = None
    date: Optional[str] = None


class ExpenseResponse(BaseModel):
    id: str
    organization_id: Optional[str] = None
    election_id: Optional[str] = None
    title: Optional[str] = None
    category: str
    amount: float
    date: Optional[str] = None
    expense_date: Optional[str] = None
    note: Optional[str] = ""
    notes: Optional[str] = ""
    mode: Optional[str] = "UPI / Online"
    user: Optional[str] = "Admin"
    vendor_name: Optional[str] = None
    receiptUrl: Optional[str] = None
    receipt_url: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class BudgetSummary(BaseModel):
    budgetLimit: float = 150000.0
    totalSpent: float = 0.0
    remaining: float = 150000.0
    utilizedPercent: int = 0
    budget_limit: float = 150000.0
    total_spent: float = 0.0
    utilized_percent: float = 0.0
    expense_count: int = 0
    expenseCount: int = 0

    model_config = ConfigDict(from_attributes=True)
