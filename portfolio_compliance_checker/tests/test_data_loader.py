"""Tests for reading the trade CSV and portfolio JSON inputs."""

import json
from pathlib import Path

import pytest

from src.data_loader import load_portfolio_references, load_trades


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_all_twenty_supplied_trades_load_in_order():
    """The real supplied CSV has 20 rows, kept in its original order."""
    trades = load_trades(PROJECT_ROOT / "data" / "proposed_trades.csv")
    assert len(trades) == 20
    assert [trade["trade_row_number"] for trade in trades] == list(range(1, 21))
    assert trades[0]["security_id"] == "AAPL"
    assert trades[-1]["security_id"] == "TCS"
    assert trades[6]["quantity"] == "-10"


def test_trade_csv_missing_required_column_is_rejected(tmp_path):
    """A CSV missing required column names cannot be processed."""
    path = tmp_path / "trades.csv"
    path.write_text("portfolio_id,security_id\nP1,A\n", encoding="utf-8")
    with pytest.raises(ValueError, match="missing required columns"):
        load_trades(path)


def test_empty_trade_file_is_handled(tmp_path):
    """An empty file is reported as an input error."""
    path = tmp_path / "empty.csv"
    path.write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="empty"):
        load_trades(path)


def test_malformed_trade_record_is_reported(tmp_path):
    """A row with too many values is rejected instead of silently truncated."""
    path = tmp_path / "malformed.csv"
    path.write_text(
        "portfolio_id,security_id,action,quantity,price,security_type\n"
        "P1,A,Buy,1,10,Equity,unexpected\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Malformed trade input CSV"):
        load_trades(path)


def test_invalid_reference_json_is_reported(tmp_path):
    """Broken JSON syntax is reported with a useful error."""
    path = tmp_path / "refs.json"
    path.write_text("{", encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid portfolio reference JSON"):
        load_portfolio_references(path)


def test_reference_loader_preserves_decimal_precision(tmp_path):
    """JSON decimal numbers are loaded as Decimal, not binary floats."""
    path = tmp_path / "refs.json"
    path.write_text(
        json.dumps({"P1": {"cash_balance": 0.1}}),
        encoding="utf-8",
    )
    references = load_portfolio_references(path)
    assert str(references["P1"]["cash_balance"]) == "0.1"


def test_reference_top_level_must_be_object(tmp_path):
    """The JSON root must map portfolio IDs to their reference data."""
    path = tmp_path / "refs.json"
    path.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="must contain an object"):
        load_portfolio_references(path)
