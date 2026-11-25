"""Compliance report generation and summary statistics."""

from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from src.config import (
    APPROVED,
    EXCEL_REPORT_FILE,
    MANUAL_SIGN_OFF,
    OUTPUT_DIRECTORY,
    REJECTED,
)

# These columns appear in the same order in both audit reports.
REPORT_COLUMNS = (
    "trade_row_number",
    "portfolio_id",
    "security_id",
    "action",
    "quantity",
    "price",
    "security_type",
    "decision",
    "reason",
    "concentration_pct",
)


def generate_reports(
    results: list[Mapping[str, Any]],
    output_directory: Path = OUTPUT_DIRECTORY,
) -> tuple[Path, Path]:
    """Write the same ordered audit results to CSV and Excel."""
    # Create output/ if it has not been created yet.
    output_directory.mkdir(parents=True, exist_ok=True)
    # Reindex fixes column order and includes blank concentration values.
    frame = pd.DataFrame(results).reindex(columns=REPORT_COLUMNS)
    csv_path = output_directory / "compliance_results.csv"
    excel_path = output_directory / "compliance_results.xlsx"
    # Do not write Pandas' extra numeric row index into either report.
    frame.to_csv(csv_path, index=False)
    frame.to_excel(excel_path, index=False, engine="openpyxl")
    return csv_path, excel_path


def build_summary(
    results: list[Mapping[str, Any]],
) -> dict[str, Any]:
    """Calculate total and per-portfolio decision counts."""
    # Start all counters at zero so an empty result list still has a clear summary.
    summary: dict[str, Any] = {
        "total": len(results),
        "approved": 0,
        "rejected": 0,
        "needs_manual_sign_off": 0,
        "by_portfolio": {},
    }
    for result in results:
        # Convert each decision label into the matching overall counter.
        decision = result["decision"]
        if decision == APPROVED:
            key = "approved"
        elif decision == REJECTED:
            key = "rejected"
        elif decision == MANUAL_SIGN_OFF:
            key = "needs_manual_sign_off"
        else:
            raise ValueError(f"Unknown decision value: {decision}")
        summary[key] += 1

        # Keep a separate set of counts for every portfolio ID.
        portfolio_id = str(result.get("portfolio_id", ""))
        portfolio_summary = summary["by_portfolio"].setdefault(
            portfolio_id,
            {
                APPROVED: 0,
                REJECTED: 0,
                MANUAL_SIGN_OFF: 0,
            },
        )
        portfolio_summary[decision] += 1
    return summary


def format_summary(summary: Mapping[str, Any]) -> str:
    """Format summary counts for the command-line application."""
    # Build readable lines so the same values can be printed as one report.
    lines = [
        f"Total trades processed: {summary['total']}",
        f"Approved: {summary['approved']}",
        f"Rejected: {summary['rejected']}",
        f"Needs Manual Sign-off: {summary['needs_manual_sign_off']}",
        "Decision breakdown by portfolio:",
    ]
    for portfolio_id, counts in sorted(summary["by_portfolio"].items()):
        lines.append(
            f"  {portfolio_id}: Approved={counts[APPROVED]}, "
            f"Rejected={counts[REJECTED]}, "
            f"Needs Manual Sign-off={counts[MANUAL_SIGN_OFF]}"
        )
    return "\n".join(lines)
