import pytest
from app.core.exceptions import ValidationException
from app.schemas.expense import ExpenseCreate
from app.services.expense_service import ExpenseService


@pytest.mark.asyncio
async def test_expense_within_budget_success(db_session, test_org):
    service = ExpenseService(db_session)
    summary_before = await service.get_budget_summary(test_org.id)
    initial_spent = summary_before.totalSpent

    expense_data = ExpenseCreate(
        category="Sound & Mic Rental",
        amount=5000.0,
        note="Ward 02 Sabha",
        mode="UPI / Online",
        user="Admin"
    )
    res = await service.add_expense(expense_data, organization_id=test_org.id)
    assert res.id.startswith("exp_")
    assert res.amount == 5000.0

    summary_after = await service.get_budget_summary(test_org.id)
    assert summary_after.totalSpent == initial_spent + 5000.0
    assert summary_after.budgetLimit == 150000.0


@pytest.mark.asyncio
async def test_expense_statutory_budget_ceiling_enforced(db_session, test_org):
    service = ExpenseService(db_session)
    summary = await service.get_budget_summary(test_org.id)
    excess_amount = (150000.0 - summary.totalSpent) + 1000.0

    expense_data = ExpenseCreate(
        category="Luxury Helicopter Campaign",
        amount=excess_amount,
        note="Exceeds statutory limit",
        mode="Cheque",
        user="Candidate"
    )

    with pytest.raises(ValidationException) as exc_info:
        await service.add_expense(expense_data, organization_id=test_org.id)

    assert "Statutory Budget Violation" in str(exc_info.value)
    assert "150,000" in str(exc_info.value)


@pytest.mark.asyncio
async def test_expense_invalid_negative_amount(db_session, test_org):
    service = ExpenseService(db_session)
    expense_data = ExpenseCreate(
        category="Invalid Refund",
        amount=-500.0,
        note="Invalid",
        mode="Cash Voucher",
        user="Admin"
    )
    with pytest.raises(ValidationException):
        await service.add_expense(expense_data, organization_id=test_org.id)
