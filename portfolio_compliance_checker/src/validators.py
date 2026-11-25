"""Reusable trade and portfolio reference validation functions."""

from decimal import Decimal, InvalidOperation, localcontext
from typing import Any, Iterable, Mapping


def parse_decimal(value: Any) -> Decimal | None:
    """Return a finite Decimal for supported scalar input, otherwise None."""
    # Booleans can be converted to numbers in Python, but are not money amounts.
    if isinstance(value, bool) or value is None:
        return None
    try:
        # str() preserves the written decimal form of CSV and JSON values.
        number = value if isinstance(value, Decimal) else Decimal(str(value).strip())
    except (InvalidOperation, ValueError, TypeError):
        return None
    # Reject NaN and infinity because they cannot be used in financial rules.
    return number if number.is_finite() else None


def decimal_working_precision(
    values: Iterable[Decimal],
    term_count: int = 1,
) -> int:
    """Choose precision that avoids rounding finite intermediate amounts."""
    # Decimal uses a limited default precision; count the input scale and size
    # so sums and products keep enough digits for exact comparisons.
    numbers = [value for value in values if value != 0]
    if not numbers:
        return 50
    largest_adjusted_exponent = max(number.adjusted() for number in numbers)
    smallest_exponent = min(number.as_tuple().exponent for number in numbers)
    span = max(0, largest_adjusted_exponent - smallest_exponent)
    return max(50, 2 * span + len(str(max(1, term_count))) + 10)


def validate_trade_input(
    trade: Mapping[str, Any],
) -> tuple[bool, Decimal | None, Decimal | None]:
    """Check quantity, price, and action before any portfolio business checks."""
    # Step 1: parse both amounts, then require positive values and an exact action.
    quantity = parse_decimal(trade.get("quantity"))
    price = parse_decimal(trade.get("price"))
    action = trade.get("action")
    valid = (
        quantity is not None
        and quantity > 0
        and price is not None
        and price > 0
        and action in ("Buy", "Sell")
    )
    return valid, quantity, price


def validate_portfolio_reference(
    reference: Any,
) -> tuple[bool, Decimal | None, Decimal | None, str | None]:
    """Validate the structure and financial values of a single portfolio."""
    # Portfolio data is separate from the trade and must be complete to proceed.
    if not isinstance(reference, Mapping):
        return False, None, None, "portfolio record must be an object"

    # These are the four pieces of portfolio data required by the rule checks.
    required_fields = (
        "cash_balance",
        "restricted_securities",
        "max_position_pct",
        "current_holdings",
    )
    missing_fields = [field for field in required_fields if field not in reference]
    if missing_fields:
        return (
            False,
            None,
            None,
            "missing required field(s): " + ", ".join(missing_fields),
        )

    # Cash cannot be negative because it is used to pay for buy orders.
    cash_balance = parse_decimal(reference["cash_balance"])
    if cash_balance is None or cash_balance < 0:
        return False, None, None, "cash_balance must be a non-negative number"

    # The cap is stored as a fraction: 0.30 means thirty percent.
    max_position_pct = parse_decimal(reference["max_position_pct"])
    if (
        max_position_pct is None
        or max_position_pct < 0
        or max_position_pct > 1
    ):
        return (
            False,
            None,
            None,
            "max_position_pct must be a number between 0 and 1",
        )

    # A restriction list must contain security IDs that can be compared safely.
    restricted = reference["restricted_securities"]
    if not isinstance(restricted, list) or not all(
        isinstance(security_id, str) and security_id.strip()
        for security_id in restricted
    ):
        return (
            False,
            None,
            None,
            "restricted_securities must be a list of non-empty strings",
        )

    # Validate every holding because each one can affect sells or concentration.
    holdings = reference["current_holdings"]
    if not isinstance(holdings, list):
        return False, None, None, "current_holdings must be a list"
    for index, holding in enumerate(holdings):
        if not isinstance(holding, Mapping):
            return (
                False,
                None,
                None,
                f"current_holdings[{index}] must be an object",
            )
        # Each holding needs an ID, a non-negative quantity, and a positive price.
        for field in ("security_id", "quantity", "market_price"):
            if field not in holding:
                return (
                    False,
                    None,
                    None,
                    f"current_holdings[{index}] is missing {field}",
                )
        if not isinstance(holding["security_id"], str) or not holding[
            "security_id"
        ].strip():
            return (
                False,
                None,
                None,
                f"current_holdings[{index}].security_id must be non-empty",
            )
        quantity = parse_decimal(holding["quantity"])
        market_price = parse_decimal(holding["market_price"])
        if quantity is None or quantity < 0:
            return (
                False,
                None,
                None,
                f"current_holdings[{index}].quantity must be non-negative",
            )
        if market_price is None or market_price <= 0:
            return (
                False,
                None,
                None,
                f"current_holdings[{index}].market_price must be positive",
            )

    return True, cash_balance, max_position_pct, None


def held_quantity(
    reference: Mapping[str, Any],
    security_id: str,
) -> Decimal:
    """Aggregate all holding entries for the requested security."""
    # A security may appear on multiple rows, so add every matching quantity.
    quantities = []
    for holding in reference["current_holdings"]:
        if holding["security_id"] == security_id:
            quantity = parse_decimal(holding["quantity"])
            if quantity is None:
                raise ValueError("Invalid holding quantity after reference validation.")
            quantities.append(quantity)
    with localcontext() as context:
        # Use enough digits so adding many holdings does not round the total.
        context.prec = decimal_working_precision(quantities, len(quantities))
        return sum(quantities, Decimal("0"))


def is_security_restricted(
    reference: Mapping[str, Any],
    security_id: str,
) -> bool:
    """Return whether the portfolio restricts the requested security."""
    # Step 2: membership in the portfolio's list means the trade is prohibited.
    return security_id in reference["restricted_securities"]


def validate_sell_holdings(
    reference: Mapping[str, Any],
    security_id: str,
    sell_quantity: Decimal,
) -> bool:
    """Check that the portfolio owns enough of the security to sell."""
    # Exact equality is allowed: the portfolio may sell its full holding.
    return held_quantity(reference, security_id) >= sell_quantity


def validate_buy_affordability(
    cash_balance: Decimal,
    quantity: Decimal,
    price: Decimal,
) -> bool:
    """Check affordability, allowing a purchase to use the exact cash balance."""
    # Step 4: compare the full cost to cash; spending all cash is permitted.
    with localcontext() as context:
        context.prec = decimal_working_precision(
            (cash_balance, quantity, price),
            3,
        )
        return quantity * price <= cash_balance
