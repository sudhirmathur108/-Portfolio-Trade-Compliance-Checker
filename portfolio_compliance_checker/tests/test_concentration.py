from decimal import Decimal

import pytest

from src.compliance import evaluate_trade
from src.concentration import calculate_concentration
from src.config import APPROVED, MANUAL_SIGN_OFF, REJECTED


def calculate(trade, reference):
    return calculate_concentration(
        trade,
        reference,
        Decimal(str(reference["cash_balance"])),
        Decimal(str(reference["max_position_pct"])),
        Decimal(str(trade["quantity"])),
        Decimal(str(trade["price"])),
    )


def test_concentration_below_limit_is_approved(valid_trade):
    reference = {
        "cash_balance": "1000",
        "restricted_securities": [],
        "max_position_pct": "0.5",
        "current_holdings": [],
    }
    assert evaluate_trade(valid_trade, reference)["decision"] == APPROVED


def test_exact_concentration_limit_is_approved(valid_trade):
    valid_trade.update(security_id="NEW", quantity="5", price="10")
    reference = {
        "cash_balance": "100",
        "restricted_securities": [],
        "max_position_pct": "0.5",
        "current_holdings": [],
    }
    result = evaluate_trade(valid_trade, reference)
    assert result["decision"] == APPROVED
    assert Decimal(result["concentration_pct"]) == Decimal("0.5")


def test_high_precision_exact_concentration_limit_is_approved():
    valid_trade = {
        "portfolio_id": "TEST",
        "security_id": "NEW",
        "action": "Buy",
        "quantity": "12345678901234567890123456789",
        "price": "3",
        "security_type": "Equity",
    }
    reference = {
        "cash_balance": "37037036703703703670370370367",
        "restricted_securities": [],
        "max_position_pct": "1",
        "current_holdings": [],
    }
    result = evaluate_trade(valid_trade, reference)
    assert result["decision"] == APPROVED
    assert Decimal(result["concentration_pct"]) == Decimal("1")


def test_concentration_above_limit_requires_manual_signoff(valid_trade):
    valid_trade.update(security_id="NEW", quantity="5", price="10")
    reference = {
        "cash_balance": "50",
        "restricted_securities": [],
        "max_position_pct": "0.49",
        "current_holdings": [],
    }
    assert evaluate_trade(valid_trade, reference)["decision"] == MANUAL_SIGN_OFF


def test_new_security_has_zero_existing_quantity(valid_trade):
    valid_trade.update(security_id="NEW", quantity="1", price="10")
    reference = {
        "cash_balance": "100",
        "restricted_securities": [],
        "max_position_pct": "1",
        "current_holdings": [],
    }
    assert calculate(valid_trade, reference).position_pct == Decimal("0.1")


def test_existing_quantity_is_included(valid_trade):
    valid_trade.update(security_id="AAA", quantity="2", price="10")
    reference = {
        "cash_balance": "70",
        "restricted_securities": [],
        "max_position_pct": "1",
        "current_holdings": [
            {"security_id": "AAA", "quantity": "3", "market_price": "10"}
        ],
    }
    assert calculate(valid_trade, reference).position_pct == Decimal("0.5")


def test_other_holdings_use_their_own_market_prices(valid_trade):
    valid_trade.update(security_id="AAA", quantity="1", price="10")
    reference = {
        "cash_balance": "100",
        "restricted_securities": [],
        "max_position_pct": "1",
        "current_holdings": [
            {"security_id": "BBB", "quantity": "2", "market_price": "30"}
        ],
    }
    result = calculate(valid_trade, reference)
    assert result.position_pct == Decimal("10") / Decimal("160")


def test_traded_security_is_excluded_from_other_holdings(valid_trade):
    valid_trade.update(security_id="AAA", quantity="1", price="10")
    reference = {
        "cash_balance": "100",
        "restricted_securities": [],
        "max_position_pct": "1",
        "current_holdings": [
            {"security_id": "AAA", "quantity": "2", "market_price": "99"}
        ],
    }
    result = calculate(valid_trade, reference)
    assert result.position_pct == Decimal("30") / Decimal("120")


def test_duplicate_holdings_are_aggregated(valid_trade):
    valid_trade.update(security_id="AAA", quantity="1", price="10")
    reference = {
        "cash_balance": "70",
        "restricted_securities": [],
        "max_position_pct": "1",
        "current_holdings": [
            {"security_id": "AAA", "quantity": "2", "market_price": "10"},
            {"security_id": "AAA", "quantity": "3", "market_price": "12"},
        ],
    }
    assert calculate(valid_trade, reference).position_pct == Decimal("0.5")


def test_zero_total_value_raises_clear_error(valid_trade):
    valid_trade.update(security_id="AAA", quantity="1", price="1")
    reference = {
        "cash_balance": "-1",
        "restricted_securities": [],
        "max_position_pct": "1",
        "current_holdings": [
            {"security_id": "AAA", "quantity": "1", "market_price": "1"}
        ],
    }
    with pytest.raises(ValueError, match="total portfolio value"):
        calculate_concentration(
            valid_trade,
            reference,
            Decimal("-1"),
            Decimal("1"),
            Decimal("1"),
            Decimal("1"),
        )


def test_concentration_only_applies_to_buy(valid_trade, portfolio_reference):
    valid_trade.update(action="Sell", quantity="1")
    portfolio_reference["max_position_pct"] = Decimal("0")
    result = evaluate_trade(valid_trade, portfolio_reference)
    assert result["decision"] == APPROVED
    assert result["concentration_pct"] == ""


def test_invalid_reference_values_cannot_be_approved(valid_trade):
    reference = {
        "cash_balance": "100",
        "restricted_securities": [],
        "max_position_pct": "0.5",
        "current_holdings": [
            {"security_id": "OTHER", "quantity": "1", "market_price": "0"}
        ],
    }
    result = evaluate_trade(valid_trade, reference)
    assert result["decision"] == REJECTED
    assert "Portfolio reference data error" in result["reason"]
