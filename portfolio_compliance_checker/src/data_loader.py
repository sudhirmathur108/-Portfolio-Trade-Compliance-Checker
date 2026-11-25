"""Load proposed trades and portfolio reference data."""

import csv
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pandas as pd
from pandas.errors import EmptyDataError, ParserError

from src.config import REQUIRED_TRADE_COLUMNS


def _validate_csv_records(file_path: Path) -> None:
    """Reject malformed rows before Pandas can silently reinterpret them."""
    try:
        # Check the raw row widths first; Pandas can otherwise hide extra fields.
        with file_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
            reader = csv.reader(csv_file, strict=True)
            header = next(reader, None)
            if not header:
                raise ValueError("Trade input CSV is empty or has no header.")
            if len(header) != len(set(header)):
                raise ValueError("Trade input CSV contains duplicate column names.")
            # A trade row should have one value for every header column.
            for record in reader:
                if record and len(record) != len(header):
                    raise ValueError(
                        "Malformed trade input CSV at line "
                        f"{reader.line_num}: expected {len(header)} fields, "
                        f"found {len(record)}."
                    )
    except csv.Error as error:
        raise ValueError(f"Malformed trade input CSV: {error}") from error


def load_trades(file_path: Path) -> list[dict[str, Any]]:
    """Load CSV trades in their original order and validate the CSV schema."""
    # Fail clearly instead of letting Pandas report a confusing lower-level error.
    if not file_path.is_file():
        raise FileNotFoundError(f"Trade input file not found: {file_path}")

    _validate_csv_records(file_path)
    try:
        # Keep every CSV value as text; financial values become Decimal later.
        # Empty strings stay empty rather than being changed into NaN values.
        frame = pd.read_csv(file_path, dtype=str, keep_default_na=False)
    except EmptyDataError as error:
        raise ValueError("Trade input CSV is empty or has no header.") from error
    except ParserError as error:
        raise ValueError(f"Malformed trade input CSV: {error}") from error

    # Only the required fields are used, and their source order is preserved.
    missing_columns = [
        column for column in REQUIRED_TRADE_COLUMNS if column not in frame.columns
    ]
    if missing_columns:
        raise ValueError(
            "Trade input CSV is missing required columns: "
            + ", ".join(missing_columns)
        )
    if frame.empty:
        raise ValueError("Trade input CSV contains no trade records.")

    # Convert each CSV row to a dictionary and number rows for the audit report.
    records = frame.loc[:, REQUIRED_TRADE_COLUMNS].to_dict(orient="records")
    for row_number, trade in enumerate(records, start=1):
        trade["trade_row_number"] = row_number
    return records


def load_portfolio_references(file_path: Path) -> dict[str, Any]:
    """Load JSON reference data without converting financial numbers to floats."""
    # Missing reference data must be reported; it must never become sample data.
    if not file_path.is_file():
        raise FileNotFoundError(
            f"Portfolio reference file not found: {file_path}"
        )

    try:
        with file_path.open("r", encoding="utf-8") as reference_file:
            # Parse JSON numbers directly as Decimal to avoid binary float errors.
            data = json.load(
                reference_file,
                parse_float=Decimal,
                parse_int=Decimal,
            )
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid portfolio reference JSON: {error}") from error

    # The outer JSON object maps each portfolio ID to its reference details.
    if not isinstance(data, dict):
        raise ValueError("Portfolio reference JSON must contain an object.")
    return data
