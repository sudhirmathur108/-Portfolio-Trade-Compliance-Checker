"""Application paths and shared constants."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TRADES_FILE = PROJECT_ROOT / "data" / "proposed_trades.csv"
PORTFOLIO_REFERENCE_FILE = PROJECT_ROOT / "data" / "portfolio_reference.json"
OUTPUT_DIRECTORY = PROJECT_ROOT / "output"
LOG_DIRECTORY = PROJECT_ROOT / "logs"
CSV_REPORT_FILE = OUTPUT_DIRECTORY / "compliance_results.csv"
EXCEL_REPORT_FILE = OUTPUT_DIRECTORY / "compliance_results.xlsx"
LOG_FILE = LOG_DIRECTORY / "compliance_checker.log"

REQUIRED_TRADE_COLUMNS = (
    "portfolio_id",
    "security_id",
    "action",
    "quantity",
    "price",
    "security_type",
)

APPROVED = "Approved"
REJECTED = "Rejected"
MANUAL_SIGN_OFF = "Needs Manual Sign-off"

INVALID_TRADE_REASON = "Invalid trade data."
RESTRICTED_SECURITY_REASON = "Security is restricted for this portfolio."
INSUFFICIENT_HOLDINGS_REASON = "Insufficient holdings to sell."
INSUFFICIENT_CASH_REASON = "Insufficient cash for this buy order."
CONCENTRATION_REASON = (
    "Exceeds maximum position concentration — requires approval."
)
APPROVED_REASON = "Trade passed all compliance checks."
