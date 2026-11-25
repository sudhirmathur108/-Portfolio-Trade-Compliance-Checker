# Project Guide: Portfolio Trade Order Compliance & Execution Checker

This guide explains the project in everyday language. You can read it before
opening the code, then use the file guide and trainer questions to review what
you have learned.

## 1. The project in one sentence

This program checks whether each proposed stock, bond, or ETF order follows a
portfolio's rules, then reports **Approved**, **Rejected**, or **Needs Manual
Sign-off** with a reason.

It is a **checker**, not a trading system. It never sends orders to a broker or
makes a real trade.

## 2. Why the project is useful

A proposed order should not be sent blindly. For example:

- A portfolio may not have enough cash to buy something.
- It may not own enough shares to sell.
- A security may be restricted.
- A buy may make one security too large a part of the portfolio.
- A trade may contain an invalid quantity, price, or action.

The checker applies these rules in a fixed order. The first rejection reason is
the result for that trade.

## 3. Project map

```text
portfolio_compliance_checker/
  data/
    proposed_trades.csv          Proposed orders to check
    portfolio_reference.json    Portfolio facts needed to check orders
  src/
    config.py                   Shared paths, decisions, and reason text
    data_loader.py              Reads and checks CSV and JSON files
    validators.py               Checks trade and portfolio input values
    compliance.py               Runs the rules in order
    concentration.py            Calculates buy concentration
    report_generator.py         Writes reports and calculates summaries
    main.py                     Runs the whole application
  tests/
    conftest.py                 Shared synthetic test examples
    test_*.py                   Automated checks for individual features
  output/                       Generated CSV and Excel results
  logs/                         Application log
  requirements.txt              Python package list
  README.md                     Quick start and reference
  PROJECT_GUIDE.md              This detailed learning guide
```

### How the files work together

1. `main.py` starts the program.
2. `data_loader.py` reads the proposed trades and portfolio facts.
3. `compliance.py` asks the validators to check each trade.
4. `concentration.py` performs the buy-only concentration calculation.
5. `report_generator.py` saves results and prepares summary counts.
6. `main.py` prints the summary and writes progress to the log.

## 4. The input files

### `data/proposed_trades.csv`

This file contains **20 proposed trades**, in the order they should be checked.
Every row has these columns:

| Column | Meaning |
|---|---|
| `portfolio_id` | Which portfolio owns or proposes the trade |
| `security_id` | Identifier for the security, such as AAPL |
| `action` | `Buy` or `Sell` |
| `quantity` | Number of shares or units in the proposed order |
| `price` | Proposed price per share or unit |
| `security_type` | Category such as Equity, Bond, or ETF |

The program keeps `security_type` in the output, but does not apply extra rules
based on it.

### `data/portfolio_reference.json`

This JSON file supplies facts used to check a portfolio:

| Field | Meaning |
|---|---|
| `cash_balance` | Cash available to pay for buys |
| `restricted_securities` | Security IDs that the portfolio must not trade |
| `max_position_pct` | Maximum allowed fraction of portfolio value in one security |
| `current_holdings` | Existing security quantities and their market prices |

The required shape for one holding is:

```json
{
  "security_id": "A_SECURITY",
  "quantity": "10",
  "market_price": "25.50"
}
```

Use the portfolio's real, approved reference data when running real checks.
Numbers are written as strings in this example to make their exact decimal
values clear. The project's current reference file is `{}` because no actual
portfolio balances, holdings, restrictions, or limits were supplied. **Do not
copy test values into this file and treat them as real.** With `{}`, the program
will reject valid-looking trades because their portfolio data is missing.

## 5. What happens to one trade

The main function for one order is:

```text
evaluate_trade(trade, portfolio_reference)
```

It returns a result containing the original trade details, a decision, a
reason, and a concentration percentage if that calculation was reached.

### Rule 1: Validate the trade

The quantity and price must be finite numbers greater than zero. The action
must be exactly `Buy` or `Sell`.

- If any condition fails: **Rejected — Invalid trade data.**
- The program stops checking this trade immediately.

Example: a quantity of `-10` is invalid, even if the portfolio data is missing.

### Reference-data check

After the trade itself passes Rule 1, the program checks that its portfolio
reference exists and has valid fields. If data is missing or malformed, the
result is **Rejected** with a `Portfolio reference data error` reason.

This is a data-quality error, not one of the ordinary business-rule outcomes.
The program must never approve a trade when it cannot check the required facts.

### Rule 2: Check restricted securities

If the trade's security ID is listed in `restricted_securities`, reject it:

> Security is restricted for this portfolio.

This check happens before checking sell holdings or buy cash.

### Rule 3: Check sells

For a sell, add together all holding rows for that security. The total must be
at least the requested sell quantity.

```text
available quantity >= sell quantity
```

If there are not enough shares, the result is **Rejected — Insufficient
holdings to sell.** Selling exactly all shares held is allowed.

A valid sell does **not** go through the buy concentration calculation.

### Rule 4: Check buy affordability

For a buy, calculate:

```text
buy cost = quantity × price
```

The cost must be less than or equal to available cash. If it is greater, the
result is **Rejected — Insufficient cash for this buy order.** Spending exactly
all available cash is allowed.

### Rule 5: Check buy concentration

Only a buy that passed all previous checks reaches this calculation. The
program follows these steps:

1. Subtract the buy cost from cash.
2. Add the proposed quantity to any quantity already held for this security.
3. Value that security using the proposed trade price.
4. Value every *other* security using its own stored market price.
5. Add post-buy cash, the traded security's value, and the other holdings'
   value to get the total portfolio value.
6. Divide the traded security's value by the total portfolio value.

If the resulting fraction is **greater than** `max_position_pct`, the result is
**Needs Manual Sign-off**. Equality with the limit passes.

#### Small worked example

Assume these **illustrative numbers only**:

- Cash: `$1,000`
- Existing holding: 10 units of `AAA` at `$10` each
- Other holding: 5 units of `BBB` at `$20` each
- Proposed buy: 5 units of `AAA` at `$10` each
- Maximum position fraction: `0.50` (50%)

Calculation:

1. Buy cost is `5 × $10 = $50`.
2. Cash after the buy is `$1,000 - $50 = $950`.
3. `AAA` quantity after the buy is `10 + 5 = 15`.
4. `AAA` value is `15 × $10 = $150`.
5. Other holding value is `5 × $20 = $100`.
6. Total after-trade value is `$950 + $150 + $100 = $1,200`.
7. `AAA` position fraction is `$150 / $1,200 = 0.125`, or 12.5%.

Since `0.125` is below `0.50`, this buy passes the concentration rule.

### Rule 6: Approve

If the trade passes every rule that applies to it, the result is:

> Approved — Trade passed all compliance checks.

## 6. Why order and independence matter

The rules are deliberately sequential. A later rule must not replace an earlier
reason:

- Invalid quantity **and** restricted security → Rule 1's invalid-data reason.
- Restricted security **and** not enough cash → Rule 2's restriction reason.
- Unaffordable buy **and** high concentration → Rule 4's cash reason.

Each trade is checked against the same portfolio snapshot. For example, if two
buys each cost `$20` and the snapshot has `$20` cash, both are checked against
that `$20`. The checker does not simulate the first buy spending cash before
checking the second. This matches the requirement to evaluate proposals
independently.

## 7. Why the code uses `Decimal`

Regular floating-point numbers can store some decimal amounts approximately.
For example, a computer may not represent a decimal fraction exactly in binary.
The program uses Python's `Decimal` for quantities, prices, cash, and
concentration math so exact comparisons such as “cost equals cash” behave
reliably.

The CSV loader initially reads values as text. The validators then parse amounts
as `Decimal`. The JSON loader also parses numbers as `Decimal`. The calculation
chooses enough working precision for its inputs and does not round monetary
intermediate amounts.

`max_position_pct` is a fraction, not a whole percent:

- `0.30` means 30%.
- `0.50` means 50%.
- `1.00` means 100%.

## 8. What each source file does

### `src/config.py`

Defines shared file paths, required CSV columns, decision labels, and standard
reason messages. Keeping these values together avoids slightly different
spellings in different modules.

### `src/data_loader.py`

- Confirms input files exist.
- Checks CSV row shapes before Pandas reads the file.
- Uses Pandas to load the trade table while preserving its order.
- Checks that required column names exist.
- Loads the portfolio JSON and preserves numeric values as `Decimal`.
- Gives a clear error for empty, malformed, or invalid input.

### `src/validators.py`

Contains small checks with one job each:

- `parse_decimal`: safely turns a value into a finite `Decimal`.
- `validate_trade_input`: checks Rule 1.
- `validate_portfolio_reference`: checks the reference-data shape and values.
- `is_security_restricted`: checks the restriction list.
- `held_quantity`: adds duplicate rows for the same security.
- `validate_sell_holdings`: checks enough shares exist for a sale.
- `validate_buy_affordability`: checks a buy cost against cash.
- `decimal_working_precision`: avoids rounding exact intermediate amounts.

### `src/concentration.py`

Implements the six post-trade concentration calculations for a buy. It returns
both the percentage for reporting and a true/false value telling the workflow
whether the limit was exceeded.

### `src/compliance.py`

This is the decision-making workflow:

- `evaluate_trade` evaluates one trade and stops at the first rejection.
- `evaluate_all_trades` evaluates all rows in order against unchanged
  portfolio references.
- `_result` builds an audit record without changing the original trade.

### `src/report_generator.py`

Creates ordered CSV and Excel reports, counts each decision, groups counts by
portfolio, and formats the console summary.

### `src/main.py`

Connects the modules into the runnable application: configure logging, load
inputs, evaluate trades, write reports, print the summary, and report processing
errors.

## 9. Results, summaries, and logs

After a successful run, the project creates:

- `output/compliance_results.csv` — easy to open or process as a table.
- `output/compliance_results.xlsx` — spreadsheet version of the same results.
- `logs/compliance_checker.log` — start/completion, input loading, trade count,
  output paths, and processing errors.

Each result row includes:

- Trade row number (the first trade is row 1; the CSV header is not counted).
- Original trade fields, including `security_type`.
- Decision and explanation.
- Concentration percentage if the concentration check was reached.

The summary shows total trades, counts for each decision, and a per-portfolio
breakdown. Counts should add up to the total processed.

With the current empty portfolio reference file, running the supplied 20 rows
gives 20 rejections: 19 have missing portfolio reference data, and the row with
negative quantity is rejected as invalid trade data before reference lookup.

## 10. Tests and synthetic data

Tests use made-up portfolios only inside test fixtures. These values are
isolated from `data/portfolio_reference.json`, so test examples do not become
real business data.

The test files cover:

- `test_validators.py`: valid, missing, invalid, and non-finite trade values.
- `test_reference_validation.py`: missing fields and malformed portfolio data.
- `test_restricted_security.py`: restricted checks and their priority.
- `test_sell_validation.py`: sells below, equal to, and above holdings.
- `test_buy_affordability.py`: buys below, equal to, and above available cash.
- `test_concentration.py`: limits, existing and duplicate holdings, stored
  prices, zero totals, and sells skipping concentration.
- `test_data_loader.py`: real 20-row input, missing columns, malformed rows,
  invalid JSON, and Decimal parsing.
- `test_report_generator.py`: CSV/Excel contents and summary counts.
- `test_trade_workflow.py`: rule order, independent snapshots, and an
  end-to-end run that creates and checks both reports.

The last full test run completed with **97 passing tests**.

## 11. How to run it in Windows PowerShell

Open the `portfolio_compliance_checker` folder in VS Code, then open a
PowerShell terminal in that folder.

Create and activate a virtual environment:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the project's packages:

```powershell
python -m pip install -r requirements.txt
```

Run the application:

```powershell
python -m src.main
```

Run all tests:

```powershell
python -m pytest -v
```

The application can run with the empty reference template, but valid trades
will be rejected for missing portfolio information. To get meaningful
portfolio-specific decisions, add verified actual reference data first.

## 12. Important limitations

- The application checks trades but never executes them.
- It does not retrieve portfolio data from a bank, broker, or market feed.
- The current project has no actual portfolio reference data.
- Every trade is evaluated independently; the program does not simulate
  portfolio changes across the trade list.
- Concentration is checked for buys only, as specified by the business rules.
- `security_type` is retained but no extra rules are inferred from it.
- The sample values in examples and tests are not business inputs.

## 13. Questions a trainer may ask

**What problem does the application solve?**  
It checks proposed portfolio orders against basic data, restriction, holdings,
cash, and concentration rules before execution.

**Does it send trades to a broker?**  
No. It only returns decisions and creates reports.

**What are the possible decisions?**  
Approved, Rejected, and Needs Manual Sign-off. Missing or invalid portfolio
data is reported as an explicit rejection with a data-error reason.

**Why are the rules checked in order?**  
The requirements say to stop at the first rejection. This makes the reason
predictable and ensures restrictions are considered before cash or holdings.

**Why can an order exactly equal to cash or holdings pass?**  
The comparisons allow equality: buy cost must be less than or equal to cash,
and sell quantity must be less than or equal to available holdings.

**Why does concentration only apply to buys?**  
That is the defined business rule. Sells are checked for holdings and then skip
concentration review.

**Why is `Decimal` used?**  
It supports exact decimal financial values and safer comparisons at boundaries.

**Can one proposed trade affect another?**  
No. Each is evaluated against the same unchanged reference snapshot.

**Why are all normal trades rejected when the app is first run?**  
The actual portfolio data was not provided. The reference JSON is `{}`, and the
system must never guess cash, holdings, restrictions, or limits.

**How do you know the program works?**  
Automated tests cover input validation, every rule and boundary, rule priority,
CSV/JSON handling, report generation, summary reconciliation, and an end-to-end
application run with isolated synthetic test data.

## 14. Quick glossary

| Term | Simple meaning |
|---|---|
| Trade | One proposed buy or sell order |
| Portfolio | An account with cash and investments |
| Reference data | Facts about a portfolio used to check an order |
| Holding | A security and the quantity currently owned |
| Restricted security | A security that this portfolio is not allowed to trade |
| Position | The portfolio's value in one security |
| Concentration | The fraction of the portfolio in that one security |
| Snapshot | A fixed copy of portfolio facts used for independent checks |
| Audit row | The output row showing the input, decision, and reason |
| Synthetic data | Fake test-only data that is not actual portfolio information |

## 15. A short explanation to practice

> “This is a Python pre-trade checker. It loads proposed orders from CSV and
> portfolio reference data from JSON. For each trade, it validates the input,
> checks restrictions, verifies sell holdings or buy cash, and checks buy
> concentration. It returns a decision and reason, creates CSV and Excel
> reports, and prints summary counts. It uses Decimal for financial values and
> checks each trade against the same portfolio snapshot. It never executes a
> trade. The real portfolio JSON is empty because actual balances and holdings
> were not supplied, so real decisions require verified reference data.”
