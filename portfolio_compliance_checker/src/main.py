"""Command-line entry point for the compliance checker."""

import logging
import sys

from src.config import (
    CSV_REPORT_FILE,
    EXCEL_REPORT_FILE,
    LOG_DIRECTORY,
    LOG_FILE,
    PORTFOLIO_REFERENCE_FILE,
    TRADES_FILE,
)
from src.compliance import evaluate_all_trades
from src.data_loader import load_portfolio_references, load_trades
from src.report_generator import build_summary, format_summary, generate_reports


def configure_logging() -> logging.Logger:
    """Configure a file log for application lifecycle and processing events."""
    LOG_DIRECTORY.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
            logging.StreamHandler(),
        ],
        force=True,
    )
    return logging.getLogger("portfolio_compliance_checker")


def main() -> int:
    """Load inputs, evaluate trades, write reports, and print summary."""
    logger = configure_logging()
    logger.info("Application started.")
    try:
        logger.info("Loading proposed trades from %s", TRADES_FILE)
        trades = load_trades(TRADES_FILE)
        logger.info("Loading portfolio references from %s", PORTFOLIO_REFERENCE_FILE)
        portfolio_references = load_portfolio_references(PORTFOLIO_REFERENCE_FILE)

        results = evaluate_all_trades(trades, portfolio_references)
        logger.info("Processed %d trades.", len(results))

        csv_path, excel_path = generate_reports(results)
        logger.info("CSV report written to %s", csv_path)
        logger.info("Excel report written to %s", excel_path)

        summary = build_summary(results)
        print(format_summary(summary))
        logger.info("Application completed.")
        return 0
    except (OSError, ValueError, RuntimeError) as error:
        logger.exception("Application processing failed.")
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
