from decimal import Decimal

from src.compliance import evaluate_trade
from src.config import (
    APPROVED,
    INSUFFICIENT_HOLDINGS_REASON,
    REJECTED,
)
from src.validators import validate_sell_holdings


def test_sell_less_than_available_holdings(portfolio_reference):
    assert validate_sell_holdings(portfolio_reference, "AAA", Decimal("9"))


def test_sell_exactly_available_holdings_passes(portfolio_reference):
    assert validate_sell_holdings(portfolio_reference, "AAA", Decimal("10"))


def test_sell_greater_than_available_holdings_fails(portfolio_reference):
    assert not validate_sell_holdings(portfolio_reference, "AAA", Decimal("11"))


def test_sell_insufficient_holdings_is_rejected(portfolio_reference, valid_trade):
    valid_trade.update(action="Sell", quantity="11")
    result = evaluate_trade(valid_trade, portfolio_reference)
    assert result["decision"] == REJECTED
    assert result["reason"] == INSUFFICIENT_HOLDINGS_REASON


def test_sell_skips_concentration_validation(portfolio_reference, valid_trade):
    portfolio_reference["max_position_pct"] = Decimal("0")
    valid_trade.update(action="Sell", quantity="10")
    result = evaluate_trade(valid_trade, portfolio_reference)
    assert result["decision"] == APPROVED
    assert result["concentration_pct"] == ""
