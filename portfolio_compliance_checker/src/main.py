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
    # Ensure the log folder exists before Python tries to open the log file.
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
    # A logger records progress both in the log file and in the terminal.
    logger = configure_logging()
    logger.info("Application started.")
    try:
        # Load the user's proposed orders and their portfolio reference snapshot.
        logger.info("Loading proposed trades from %s", TRADES_FILE)
        trades = load_trades(TRADES_FILE)
        logger.info("Loading portfolio references from %s", PORTFOLIO_REFERENCE_FILE)
        portfolio_references = load_portfolio_references(PORTFOLIO_REFERENCE_FILE)

        # The compliance engine returns one decision for each input row.
        results = evaluate_all_trades(trades, portfolio_references)
        logger.info("Processed %d trades.", len(results))

        # Save both report formats before displaying the summary.
        csv_path, excel_path = generate_reports(results)
        logger.info("CSV report written to %s", csv_path)
        logger.info("Excel report written to %s", excel_path)

        # Print counts so users can quickly see the outcome of the whole batch.
        summary = build_summary(results)
        print(format_summary(summary))
        logger.info("Application completed.")
        return 0
    except (OSError, ValueError, RuntimeError) as error:
        # Log the full error details and show a short message to the user.
        logger.exception("Application processing failed.")
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
