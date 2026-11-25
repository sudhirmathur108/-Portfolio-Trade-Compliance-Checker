# Portfolio Trade Order Compliance & Execution Checker

## Overview

This Python application checks proposed portfolio trades before execution. It
does not place orders or connect to a broker. It evaluates each trade
independently against a portfolio reference snapshot and produces a decision
and an explanation.

The supplied trade file contains 20 proposals. Actual portfolio balances,
holdings, restrictions, and concentration limits were not supplied. Therefore,
`data/portfolio_reference.json` is intentionally an empty JSON object (`{}`),
not fabricated business data. Until real reference data is entered, each
otherwise-valid trade is rejected with a clear missing-reference-data error.

## Technology

- Python 3.10+
- Pandas for CSV input and tabular reports
- JSON portfolio reference data
- `Decimal` for financial calculations
- Openpyxl for Excel output
- Pytest for automated tests
- Python logging

## Project layout

```text
portfolio_compliance_checker/
  data/
    proposed_trades.csv
    portfolio_reference.json
  src/
    config.py
    data_loader.py
    validators.py
    compliance.py
    concentration.py
    report_generator.py
    main.py
  tests/
  output/
  logs/
  requirements.txt
```

## Install (Windows PowerShell / VS Code)

Open a PowerShell terminal in the project root:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell prevents activation, you can invoke the venv interpreter directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Input data

### Proposed trades

`data/proposed_trades.csv` has exactly 20 records and these columns:

```text
portfolio_id,security_id,action,quantity,price,security_type
```

The records and their order are preserved. `security_type` is retained in
reports but does not introduce extra validation rules.

### Portfolio references

Enter one object per real portfolio in `data/portfolio_reference.json`:

```json
{
  "POR001": {
    "cash_balance": "100000",
    "restricted_securities": [],
    "max_position_pct": "0.30",
    "current_holdings": [
      {
        "security_id": "AAPL",
        "quantity": "100",
        "market_price": "150"
      }
    ]
  }
}
```

The values above only illustrate the required format; they are not supplied
business data and are not included in the live reference file. Decimal values
may be represented as strings to preserve exactness. Cash and holding quantities
must be non-negative; market prices must be positive; concentration limits must
be between zero and one inclusive. Repeated holding entries are allowed and
their quantities are aggregated for the traded security.

## Compliance sequence

Checks stop at the first rejection, in this order:

1. **Trade data:** quantity and price must be positive numbers and action must
   be `Buy` or `Sell`. Otherwise the result is `Rejected` with
   `Invalid trade data.`
2. **Restricted security:** restricted securities are rejected before other
   portfolio checks.
3. **Sell holdings:** a sell is allowed only when available holdings are at
   least the requested quantity. Sells do not receive a concentration check.
4. **Buy affordability:** buy cost must not exceed cash. Spending exactly the
   available cash is allowed.
5. **Buy concentration:** uses post-trade cash, the traded security valued at
   the proposed trade price, and the other holdings valued at their own stored
   market prices. A percentage strictly above the cap needs manual sign-off;
   equality passes.
6. **Approval:** if applicable checks pass, the trade is approved.

Missing or malformed portfolio reference data is rejected with an explicit data
error. Each proposed trade is checked against the same unchanged reference
snapshot; one row does not consume cash or holdings for later rows. No
intermediate monetary values are rounded.

## Run the application

From the project root:

```powershell
python -m src.main
```

The application writes:

- `output/compliance_results.csv`
- `output/compliance_results.xlsx`
- `logs/compliance_checker.log`

With the untouched empty reference template, valid trades are rejected because
their portfolios have no reference data. To see the compliance outcomes for
real portfolios, populate the reference JSON first.

The console summary shows total trades, counts by decision, and a per-portfolio
breakdown. The counts reconcile to the total number processed. Each report row
includes the trade record number, original trade fields, decision, reason, and
concentration percentage where that check was reached. It is blank when
concentration was not reached.

## Run automated tests

The tests use separate synthetic fixtures and do not modify or populate the
actual portfolio reference file.

```powershell
pytest -v
```

## Limitations and assumptions

- This is a pre-trade checker only; it never submits or executes trades.
- Reference data is supplied by the user and is not fetched from any external
  system.
- Each trade is intentionally evaluated independently against the same
  reference snapshot rather than simulating a sequence of portfolio changes.
- Concentration is checked only for buys, using the proposed price for the
  traded security and stored market prices for all other holdings.
- `max_position_pct` is a decimal fraction (for example, `0.30` means 30%).
- If the input CSV schema or top-level JSON structure is unusable, the
  application logs and reports the processing error rather than writing
  misleading results.
