from typing import Optional
from pydantic import BaseModel, ConfigDict


class ExpenseBase(BaseModel):
    category: str
    amount: float
    note: Optional[str] = ""
    mode: Optional[str] = "UPI / Online"  # UPI / Online, Cash Voucher, Bank Transfer, Cheque
    user: Optional[str] = "Admin"
    receiptUrl: Optional[str] = None


class ExpenseCreate(ExpenseBase):
    date: Optional[str] = None


class ExpenseResponse(ExpenseBase):
    id: str
    date: str

    model_config = ConfigDict(from_attributes=True)


class BudgetSummary(BaseModel):
    budgetLimit: float
    totalSpent: float
    remaining: float
    utilizedPercent: int
