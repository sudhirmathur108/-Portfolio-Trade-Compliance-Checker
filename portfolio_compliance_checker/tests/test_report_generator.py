"""Tests for CSV/Excel reports and the printed summary."""

import pandas as pd

from src.config import APPROVED, MANUAL_SIGN_OFF, REJECTED
from src.report_generator import build_summary, generate_reports


def sample_results():
    """Make one example of each decision type for report tests."""
    return [
        {
            "trade_row_number": 1,
            "portfolio_id": "P1",
            "security_id": "AAA",
            "action": "Buy",
            "quantity": "1",
            "price": "10",
            "security_type": "Equity",
            "decision": APPROVED,
            "reason": "Passed",
            "concentration_pct": "0.1",
        },
        {
            "trade_row_number": 2,
            "portfolio_id": "P1",
            "security_id": "BBB",
            "action": "Sell",
            "quantity": "1",
            "price": "10",
            "security_type": "Bond",
            "decision": REJECTED,
            "reason": "Rejected",
            "concentration_pct": "",
        },
        {
            "trade_row_number": 3,
            "portfolio_id": "P2",
            "security_id": "CCC",
            "action": "Buy",
            "quantity": "1",
            "price": "10",
            "security_type": "ETF",
            "decision": MANUAL_SIGN_OFF,
            "reason": "Review",
            "concentration_pct": "0.8",
        },
    ]


def test_csv_and_excel_reports_are_generated(tmp_path):
    """Both reports contain the decisions in the same order as the input."""
    csv_path, excel_path = generate_reports(sample_results(), tmp_path)
    assert csv_path.exists()
    assert excel_path.exists()
    csv_data = pd.read_csv(csv_path, keep_default_na=False)
    excel_data = pd.read_excel(excel_path, keep_default_na=False)
    assert list(csv_data["security_id"]) == ["AAA", "BBB", "CCC"]
    assert list(excel_data["decision"]) == [
        APPROVED,
        REJECTED,
        MANUAL_SIGN_OFF,
    ]
    assert csv_data.loc[1, "concentration_pct"] == ""


def test_summary_counts_reconcile_by_portfolio():
    """Overall decision counts add up and portfolio counts are separated."""
    summary = build_summary(sample_results())
    assert summary["total"] == 3
    assert (
        summary["approved"]
        + summary["rejected"]
        + summary["needs_manual_sign_off"]
        == summary["total"]
    )
    assert summary["by_portfolio"]["P1"][APPROVED] == 1
    assert summary["by_portfolio"]["P1"][REJECTED] == 1
