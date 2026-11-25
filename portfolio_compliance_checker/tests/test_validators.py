from decimal import Decimal

import pytest

from src.validators import validate_trade_input


@pytest.mark.parametrize(
    "missing_field",
    ["action", "quantity", "price"],
)
def test_missing_trade_parameter_is_invalid(missing_field):
    trade = {"action": "Buy", "quantity": "1", "price": "10"}
    del trade[missing_field]
    assert not validate_trade_input(trade)[0]


@pytest.mark.parametrize(
    ("action", "quantity", "price"),
    [
        ("Buy", "1", "10"),
        ("Sell", "1.5", "10.25"),
    ],
)
def test_valid_trade_data(action, quantity, price):
    valid, parsed_quantity, parsed_price = validate_trade_input(
        {"action": action, "quantity": quantity, "price": price}
    )
    assert valid
    assert isinstance(parsed_quantity, Decimal)
    assert isinstance(parsed_price, Decimal)


@pytest.mark.parametrize(
    ("action", "quantity", "price"),
    [
        ("Buy", "0", "10"),
        ("Buy", "-1", "10"),
        ("Buy", "1", "0"),
        ("Buy", "1", "-10"),
        ("buy", "1", "10"),
        ("Buy", "not-a-number", "10"),
        ("Buy", "1", "not-a-number"),
        ("Buy", "NaN", "10"),
        ("Buy", "Infinity", "10"),
    ],
)
def test_invalid_trade_data(action, quantity, price):
    valid, _, _ = validate_trade_input(
        {"action": action, "quantity": quantity, "price": price}
    )
    assert not valid
