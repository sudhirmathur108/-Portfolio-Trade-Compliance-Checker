from decimal import Decimal

from src.compliance import evaluate_trade
from src.config import INSUFFICIENT_CASH_REASON, REJECTED
from src.validators import validate_buy_affordability


def test_buy_cost_below_cash_balance():
    assert validate_buy_affordability(
        Decimal("100"), Decimal("2"), Decimal("10")
    )


def test_buy_cost_exactly_equal_to_cash_balance():
    assert validate_buy_affordability(
        Decimal("20"), Decimal("2"), Decimal("10")
    )


def test_high_precision_buy_cost_exactly_equal_to_cash_balance():
    quantity = Decimal("12345678901234567890123456789")
    price = Decimal("3")
    exact_cost = Decimal("37037036703703703670370370367")
    assert validate_buy_affordability(exact_cost, quantity, price)


def test_buy_cost_greater_than_cash_balance():
    assert not validate_buy_affordability(
        Decimal("19.99"), Decimal("2"), Decimal("10")
    )


def test_insufficient_cash_rejected_before_concentration(portfolio_reference, valid_trade):
    portfolio_reference["cash_balance"] = Decimal("19")
    portfolio_reference["max_position_pct"] = Decimal("0")
    result = evaluate_trade(valid_trade, portfolio_reference)
    assert result["decision"] == REJECTED
    assert result["reason"] == INSUFFICIENT_CASH_REASON
    assert result["concentration_pct"] == ""
