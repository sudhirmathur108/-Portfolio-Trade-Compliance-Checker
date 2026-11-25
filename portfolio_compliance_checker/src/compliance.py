"""Sequential trade compliance workflow."""

from typing import Any, Mapping

from src.concentration import calculate_concentration
from src.config import (
    APPROVED,
    APPROVED_REASON,
    CONCENTRATION_REASON,
    INSUFFICIENT_CASH_REASON,
    INSUFFICIENT_HOLDINGS_REASON,
    INVALID_TRADE_REASON,
    MANUAL_SIGN_OFF,
    REJECTED,
    RESTRICTED_SECURITY_REASON,
)
from src.validators import (
    is_security_restricted,
    validate_buy_affordability,
    validate_portfolio_reference,
    validate_sell_holdings,
    validate_trade_input,
)


def _result(
    trade: Mapping[str, Any],
    decision: str,
    reason: str,
    concentration_pct: str = "",
) -> dict[str, Any]:
    """Build a result while preserving all supplied trade fields."""
    result = {
        key: value
        for key, value in trade.items()
        if key in (
            "portfolio_id",
            "security_id",
            "action",
            "quantity",
            "price",
            "security_type",
            "trade_row_number",
        )
    }
    result["decision"] = decision
    result["reason"] = reason
    result["concentration_pct"] = concentration_pct
    return result


def evaluate_trade(
    trade: Mapping[str, Any],
    portfolio_reference: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Evaluate one proposed trade without mutating its portfolio snapshot."""
    valid_trade, quantity, price = validate_trade_input(trade)
    if not valid_trade:
        return _result(trade, REJECTED, INVALID_TRADE_REASON)

    if portfolio_reference is None:
        portfolio_id = trade.get("portfolio_id", "")
        return _result(
            trade,
            REJECTED,
            "Portfolio reference data error: reference data is missing for "
            f"portfolio '{portfolio_id}'.",
        )

    valid_reference, cash_balance, max_position_pct, reference_error = (
        validate_portfolio_reference(portfolio_reference)
    )
    if not valid_reference:
        return _result(
            trade,
            REJECTED,
            f"Portfolio reference data error: {reference_error}.",
        )

    security_id = trade.get("security_id")
    if is_security_restricted(portfolio_reference, security_id):
        return _result(trade, REJECTED, RESTRICTED_SECURITY_REASON)

    action = trade["action"]
    if action == "Sell":
        if not validate_sell_holdings(portfolio_reference, security_id, quantity):
            return _result(trade, REJECTED, INSUFFICIENT_HOLDINGS_REASON)
        return _result(trade, APPROVED, APPROVED_REASON)

    if not validate_buy_affordability(cash_balance, quantity, price):
        return _result(trade, REJECTED, INSUFFICIENT_CASH_REASON)

    try:
        concentration = calculate_concentration(
            trade,
            portfolio_reference,
            cash_balance,
            max_position_pct,
            quantity,
            price,
        )
    except ValueError as error:
        return _result(
            trade,
            REJECTED,
            f"Portfolio reference data error: {error}.",
        )

    if concentration.exceeds_limit:
        return _result(
            trade,
            MANUAL_SIGN_OFF,
            CONCENTRATION_REASON,
            str(concentration.position_pct),
        )
    return _result(
        trade,
        APPROVED,
        APPROVED_REASON,
        str(concentration.position_pct),
    )


def evaluate_all_trades(
    trades: list[Mapping[str, Any]],
    portfolio_references: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Evaluate trades in input order against unchanged reference snapshots."""
    results = []
    for trade in trades:
        portfolio_id = trade.get("portfolio_id")
        reference = portfolio_references.get(portfolio_id)
        results.append(evaluate_trade(trade, reference))
    return results
