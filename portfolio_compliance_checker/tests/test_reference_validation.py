"""Tests for required portfolio data and invalid reference values."""

from decimal import Decimal

import pytest

from src.config import REJECTED
from src.compliance import evaluate_trade
from src.validators import validate_portfolio_reference


def valid_reference():
    """Return a small, synthetic portfolio that passes reference validation."""
    return {
        "cash_balance": "100",
        "restricted_securities": [],
        "max_position_pct": "0.5",
        "current_holdings": [],
    }


@pytest.mark.parametrize(
    "field",
    [
        "cash_balance",
        "restricted_securities",
        "max_position_pct",
        "current_holdings",
    ],
)
def test_each_required_reference_field_is_required(field):
    """Removing any required portfolio value must make the reference invalid."""
    reference = valid_reference()
    del reference[field]
    valid, _, _, error = validate_portfolio_reference(reference)
    assert not valid
    assert field in error


@pytest.mark.parametrize(
    "cash_balance",
    ["-0.01", "NaN", "Infinity", "not-a-number", None, True],
)
def test_invalid_cash_balance_is_rejected(cash_balance, valid_trade):
    """Cash must be a finite, non-negative number."""
    reference = valid_reference()
    reference["cash_balance"] = cash_balance
    result = evaluate_trade(valid_trade, reference)
    assert result["decision"] == REJECTED
    assert "cash_balance" in result["reason"]


@pytest.mark.parametrize(
    "max_position_pct",
    ["-0.01", "1.01", "NaN", "Infinity", "not-a-number", None, True],
)
def test_invalid_concentration_limit_is_rejected(max_position_pct, valid_trade):
    """Concentration limits must be finite fractions between zero and one."""
    reference = valid_reference()
    reference["max_position_pct"] = max_position_pct
    result = evaluate_trade(valid_trade, reference)
    assert result["decision"] == REJECTED
    assert "max_position_pct" in result["reason"]


@pytest.mark.parametrize("max_position_pct", ["0", "1"])
def test_concentration_limit_inclusive_boundaries_are_valid(max_position_pct):
    """The valid concentration range includes both zero and one."""
    reference = valid_reference()
    reference["max_position_pct"] = max_position_pct
    valid, _, parsed_limit, error = validate_portfolio_reference(reference)
    assert valid
    assert parsed_limit == Decimal(max_position_pct)
    assert error is None


@pytest.mark.parametrize(
    "restricted_securities",
    [None, "AAA", [None], [""], [1]],
)
def test_invalid_restricted_security_list_is_rejected(
    restricted_securities,
    valid_trade,
):
    """Restrictions must be a list of non-empty security ID strings."""
    reference = valid_reference()
    reference["restricted_securities"] = restricted_securities
    result = evaluate_trade(valid_trade, reference)
    assert result["decision"] == REJECTED
    assert "restricted_securities" in result["reason"]


@pytest.mark.parametrize(
    "current_holdings",
    [None, {}, "not-a-list", [None], [{}], [{"security_id": "AAA"}]],
)
def test_invalid_holding_structure_is_rejected(current_holdings, valid_trade):
    """Holdings must be a list containing properly shaped records."""
    reference = valid_reference()
    reference["current_holdings"] = current_holdings
    result = evaluate_trade(valid_trade, reference)
    assert result["decision"] == REJECTED
    assert "Portfolio reference data error" in result["reason"]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("security_id", ""),
        ("security_id", None),
        ("quantity", "-1"),
        ("quantity", "NaN"),
        ("quantity", "not-a-number"),
        ("market_price", "0"),
        ("market_price", "-1"),
        ("market_price", "Infinity"),
        ("market_price", "not-a-number"),
    ],
)
def test_invalid_holding_values_are_rejected(field, value, valid_trade):
    """Holding IDs, quantities, and market prices must have valid values."""
    holding = {
        "security_id": "AAA",
        "quantity": "1",
        "market_price": "10",
    }
    holding[field] = value
    reference = valid_reference()
    reference["current_holdings"] = [holding]
    result = evaluate_trade(valid_trade, reference)
    assert result["decision"] == REJECTED
    assert "Portfolio reference data error" in result["reason"]


def test_zero_quantity_holding_is_valid():
    """A portfolio may have a holding record with zero shares."""
    reference = valid_reference()
    reference["current_holdings"] = [
        {"security_id": "AAA", "quantity": "0", "market_price": "10"}
    ]
    valid, _, _, error = validate_portfolio_reference(reference)
    assert valid
    assert error is None


def test_reference_must_be_an_object():
    """A portfolio reference must be a mapping, not a list or scalar."""
    valid, _, _, error = validate_portfolio_reference([])
    assert not valid
    assert error == "portfolio record must be an object"
