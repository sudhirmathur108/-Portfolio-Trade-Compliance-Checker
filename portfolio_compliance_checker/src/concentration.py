"""Buy-order position concentration calculation."""

from dataclasses import dataclass
from decimal import Decimal, localcontext
from typing import Any, Mapping

from src.validators import (
    decimal_working_precision,
    held_quantity,
    parse_decimal,
)


@dataclass(frozen=True)
class ConcentrationResult:
    """Calculated post-trade concentration and whether it breaches the limit."""

    position_pct: Decimal
    exceeds_limit: bool


def calculate_concentration(
    trade: Mapping[str, Any],
    reference: Mapping[str, Any],
    cash_balance: Decimal,
    max_position_pct: Decimal,
    quantity: Decimal,
    price: Decimal,
) -> ConcentrationResult:
    """Calculate post-trade concentration for a validated Buy trade."""
    reference_values = [cash_balance, max_position_pct, quantity, price]
    for holding in reference["current_holdings"]:
        holding_quantity = parse_decimal(holding["quantity"])
        market_price = parse_decimal(holding["market_price"])
        if holding_quantity is None or market_price is None:
            raise ValueError("Invalid holding values after reference validation.")
        reference_values.extend((holding_quantity, market_price))

    with localcontext() as context:
        context.prec = decimal_working_precision(
            reference_values,
            len(reference["current_holdings"]) + 4,
        )
        buy_cost = quantity * price
        post_trade_cash = cash_balance - buy_cost
        post_trade_quantity = (
            held_quantity(reference, trade["security_id"]) + quantity
        )
        post_trade_security_value = post_trade_quantity * price

        value_of_other_holdings = Decimal("0")
        for holding in reference["current_holdings"]:
            if holding["security_id"] != trade["security_id"]:
                holding_quantity = parse_decimal(holding["quantity"])
                market_price = parse_decimal(holding["market_price"])
                if holding_quantity is None or market_price is None:
                    raise ValueError(
                        "Invalid holding values after reference validation."
                    )
                value_of_other_holdings += holding_quantity * market_price

        total_portfolio_value_after = (
            post_trade_cash + post_trade_security_value + value_of_other_holdings
        )
        if (
            not total_portfolio_value_after.is_finite()
            or total_portfolio_value_after <= 0
        ):
            raise ValueError(
                "total portfolio value after the trade must be positive"
            )

        position_pct = post_trade_security_value / total_portfolio_value_after
        # Cross multiplication preserves the strict boundary without relying
        # on rounded division for the decision.
        exceeds_limit = (
            post_trade_security_value
            > max_position_pct * total_portfolio_value_after
        )
        return ConcentrationResult(position_pct, exceeds_limit)
