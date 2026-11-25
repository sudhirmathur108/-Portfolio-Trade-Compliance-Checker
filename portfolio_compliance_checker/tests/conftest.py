"""Shared synthetic portfolio and trade fixtures for tests."""

from decimal import Decimal

import pytest


@pytest.fixture
def portfolio_reference():
    """Provide safe, synthetic account data shared by the tests."""
    return {
        "cash_balance": Decimal("1000"),
        "restricted_securities": [],
        "max_position_pct": Decimal("0.5"),
        "current_holdings": [
            {
                "security_id": "AAA",
                "quantity": Decimal("10"),
                "market_price": Decimal("10"),
            },
            {
                "security_id": "BBB",
                "quantity": Decimal("10"),
                "market_price": Decimal("20"),
            },
        ],
    }


@pytest.fixture
def valid_trade():
    """Provide one well-formed buy order that tests can customize."""
    return {
        "portfolio_id": "TEST",
        "security_id": "AAA",
        "action": "Buy",
        "quantity": "2",
        "price": "10",
        "security_type": "Equity",
        "trade_row_number": 1,
    }
