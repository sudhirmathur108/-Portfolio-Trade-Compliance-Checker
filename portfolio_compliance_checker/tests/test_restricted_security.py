from decimal import Decimal

from src.compliance import evaluate_trade
from src.config import REJECTED, RESTRICTED_SECURITY_REASON
from src.validators import is_security_restricted


def test_restricted_security_is_rejected(portfolio_reference, valid_trade):
    portfolio_reference["restricted_securities"] = ["AAA"]
    result = evaluate_trade(valid_trade, portfolio_reference)
    assert result["decision"] == REJECTED
    assert result["reason"] == RESTRICTED_SECURITY_REASON


def test_unrestricted_security_passes_restriction_check(portfolio_reference):
    assert not is_security_restricted(portfolio_reference, "AAA")


def test_restricted_check_precedes_affordability(portfolio_reference, valid_trade):
    portfolio_reference["restricted_securities"] = ["AAA"]
    portfolio_reference["cash_balance"] = Decimal("1")
    result = evaluate_trade(valid_trade, portfolio_reference)
    assert result["reason"] == RESTRICTED_SECURITY_REASON
