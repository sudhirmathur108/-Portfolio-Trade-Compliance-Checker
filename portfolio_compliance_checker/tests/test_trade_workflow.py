import json
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest

import src.main as main_module
from src.compliance import evaluate_all_trades, evaluate_trade
from src.config import (
    APPROVED,
    INSUFFICIENT_CASH_REASON,
    INVALID_TRADE_REASON,
    REJECTED,
    RESTRICTED_SECURITY_REASON,
)
from src.report_generator import generate_reports


def test_invalid_trade_precedes_restricted_check(portfolio_reference, valid_trade):
    valid_trade.update(quantity="0")
    portfolio_reference["restricted_securities"] = ["AAA"]
    assert evaluate_trade(valid_trade, portfolio_reference)["reason"] == (
        INVALID_TRADE_REASON
    )


def test_restricted_precedes_insufficient_cash(portfolio_reference, valid_trade):
    portfolio_reference["restricted_securities"] = ["AAA"]
    portfolio_reference["cash_balance"] = Decimal("0")
    assert evaluate_trade(valid_trade, portfolio_reference)["reason"] == (
        RESTRICTED_SECURITY_REASON
    )


def test_missing_reference_is_never_approved(valid_trade):
    result = evaluate_trade(valid_trade, None)
    assert result["decision"] == REJECTED
    assert "reference data is missing" in result["reason"]


def test_invalid_reference_is_never_approved(valid_trade, portfolio_reference):
    del portfolio_reference["cash_balance"]
    result = evaluate_trade(valid_trade, portfolio_reference)
    assert result["decision"] == REJECTED
    assert "Portfolio reference data error" in result["reason"]


def test_trades_are_evaluated_independently(valid_trade, portfolio_reference):
    first = dict(valid_trade, quantity="90")
    second = dict(valid_trade, quantity="2")
    results = evaluate_all_trades([first, second], {"TEST": portfolio_reference})
    assert results[0]["decision"] != APPROVED
    assert results[1]["decision"] == APPROVED
    assert portfolio_reference["cash_balance"] == Decimal("1000")
    assert portfolio_reference["current_holdings"][0]["quantity"] == Decimal("10")


def test_cash_is_not_deducted_between_trades(valid_trade, portfolio_reference):
    portfolio_reference["cash_balance"] = Decimal("20")
    trades = [dict(valid_trade, quantity="2"), dict(valid_trade, quantity="2")]
    results = evaluate_all_trades(trades, {"TEST": portfolio_reference})
    assert [item["decision"] for item in results] == [APPROVED, APPROVED]


def test_affordability_precedes_concentration(portfolio_reference, valid_trade):
    portfolio_reference["cash_balance"] = Decimal("19")
    portfolio_reference["max_position_pct"] = Decimal("0")
    result = evaluate_trade(valid_trade, portfolio_reference)
    assert result["reason"] == INSUFFICIENT_CASH_REASON


def test_application_runs_with_synthetic_reference_data(tmp_path, monkeypatch, capsys):
    project_root = Path(__file__).resolve().parents[1]
    trades_path = tmp_path / "proposed_trades.csv"
    trades_path.write_text(
        (project_root / "data" / "proposed_trades.csv").read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )
    portfolio_ids = ("POR001", "POR002", "POR003", "POR004", "POR005")
    references = {
        portfolio_id: {
            "cash_balance": "1000000000",
            "restricted_securities": [],
            "max_position_pct": "1",
            "current_holdings": [],
        }
        for portfolio_id in portfolio_ids
    }
    references["POR001"]["current_holdings"] = [
        {
            "security_id": "TCS",
            "quantity": "110",
            "market_price": "310",
        }
    ]
    references["POR003"]["current_holdings"] = [
        {
            "security_id": "RELIANCE",
            "quantity": "31",
            "market_price": "2400",
        }
    ]
    references_path = tmp_path / "portfolio_reference.json"
    references_path.write_text(json.dumps(references), encoding="utf-8")
    output_directory = tmp_path / "output"
    monkeypatch.setattr(main_module, "TRADES_FILE", trades_path)
    monkeypatch.setattr(
        main_module, "PORTFOLIO_REFERENCE_FILE", references_path
    )
    monkeypatch.setattr(main_module, "LOG_DIRECTORY", tmp_path / "logs")
    monkeypatch.setattr(main_module, "LOG_FILE", tmp_path / "logs" / "test.log")
    monkeypatch.setattr(
        main_module,
        "generate_reports",
        lambda results: generate_reports(results, output_directory),
    )

    assert main_module.main() == 0
    summary_text = capsys.readouterr().out
    assert "Total trades processed: 20" in summary_text
    assert "Approved: 19" in summary_text
    assert "Rejected: 1" in summary_text
    csv_report = output_directory / "compliance_results.csv"
    excel_report = output_directory / "compliance_results.xlsx"
    assert csv_report.is_file()
    assert excel_report.is_file()
    csv_results = pd.read_csv(csv_report, dtype=str, keep_default_na=False)
    excel_results = pd.read_excel(excel_report, keep_default_na=False)
    assert len(csv_results) == len(excel_results) == 20
    assert csv_results["trade_row_number"].tolist() == [
        str(number) for number in range(1, 21)
    ]
    assert csv_results["security_type"].tolist()[0] == "Equity"
    assert csv_results["decision"].value_counts().to_dict() == {
        "Approved": 19,
        "Rejected": 1,
    }
    assert csv_results.loc[6, "reason"] == INVALID_TRADE_REASON
    input_rows = pd.read_csv(trades_path, dtype=str, keep_default_na=False)
    pd.testing.assert_frame_equal(
        csv_results.loc[:, input_rows.columns],
        input_rows,
        check_dtype=False,
    )
    assert json.loads(
        (project_root / "data" / "portfolio_reference.json").read_text(
            encoding="utf-8"
        )
    ) == {}
