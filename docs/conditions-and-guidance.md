# Conditions and personalized resilience guidance

## What was implemented

`conditions.classify_conditions(snapshot)` labels **observed conditions**, separately from `economic_outlook`'s experimental next-month predictions. It is an explainable rule classifier, not a fitted ML classifier with a measured accuracy percentage. There is no authoritative training label for a generic "bad economy." These thresholds are explicit, versioned prototype assumptions.

Economy labels: `steady`, `watch`, `pressured`, `unknown`. Components cover living costs, unemployment trend and borrowing costs. Market labels: `steady`, `watch`, `stressed`, `unknown`. A steady label means no configured stress rule triggered, not guaranteed future gains or a declaration that the economy is healthy.

| Component | Watch | Pressure / stress |
| --- | --- | --- |
| CPI inflation, year over year | At least 3% | At least 4% |
| Unemployment change, 3 months | At least 0.3 percentage points | At least 0.5 percentage points |
| Federal funds effective rate | At least 3.5% | At least 5% |
| S&P 500 drawdown from trailing 252 observed trading-day high | At least 5% below high | At least 10% below high |
| S&P 500 trailing 3-calendar-month return | Negative | At most -10% |

Economy uses the most pressured known component, with `data_complete: false` if any component is unknown. Market needs both drawdown and return. Date/finite-number checks are enforced: macro observation dates older than 100 calendar days, market dates older than 10 days and future observations are unknown. These freshness cutoffs are assumptions, not release-calendar guarantees. Current revised observations remain subject to the vintage limitations in `economic-research.md`.

## Conditions are filtered through the user's exposure

| Condition plus user situation | Guidance / scenario to explore |
| --- | --- |
| Elevated inflation plus tight cash/reserves | Illustrative 5% variable-cost increase; review optional purchases while preserving essentials |
| Rising unemployment plus tight reserves | Illustrative 10% income reduction; national data does not predict this user's income loss |
| Elevated borrowing costs plus reported variable-rate debt | Review reset terms; approximate +1 percentage-point interest shock using balance × 0.01 / 12 |
| Weak market plus equity exposure and planned equity withdrawal within 90 days | Review the goal's timing and available cash; no automatic sell instruction |
| High-interest debt plus tight cash | Preserve required payments and essential liquidity; no extra-payment recommendation |
| High-interest debt plus ample reserves and surplus | Compare an optional extra-payment scenario against retaining liquid cash |
| Weak conditions, ample cash, no relevant reported exposure | Display conditions without manufacturing an action alert |

Tight resilience means modeled checking below its buffer, modeled savings below its floor, or less than three months of liquid coverage. This is an internal heuristic. The tool does not know which expenses are essential; it must not order blanket spending cuts. No rule tells every user to spend more or less because an index moved. Cheap borrowing conditions are not an automatic reason to take a loan. Extra repayment can worsen liquidity; moving money from checking into savings does not create more combined reserves.

Required new optional customer inputs, in USD:

```json
{"variable_rate_debt_balance": 12000, "high_interest_debt_balance": 4000,
 "equity_exposure": 5000, "planned_equity_withdrawal_90d": 1000}
```

These exposures are not guessed from account type. Missing values suppress corresponding alerts, and `economic_pressure` returns `personalization_missing_fields` so the frontend can ask for missing context. A missing input does not establish absence of risk. Existing fixed-rate debt is not assumed to reprice.

`guardian.detect_risks()` now integrates these alerts. Each contains numeric evidence, `guidance`, `tradeoff`, `suggested_simulation`, a stable event key and app-delivery candidate status. Scenarios are illustrative; users must compare the recalculated result before taking action. New scenario key `additional_monthly_expense` adds a recurring expense on day 10, which allows a rate-cost shock without pretending to change a loan's contract. It is not a debt-payment or amortization calculation.

The original emergency-reserve rule no longer blindly recommends moving cash into savings; the original debt-burden rule gates extra-payment scenarios on sufficient reserves, surplus and projected checking.

## Run it

Offline example with identical stressed conditions but different customer situations:

```powershell
.venv/Scripts/python.exe -m scripts.conditions_demo
```

All indicators in that demo are **hypothetical**, explicitly labeled as such. It writes `data/synthetic/conditions-demo.json`. The cash-constrained fictional customer receives exposure alerts; the ample-cash fictional customer has no condition-driven action alert.

Observed classifications using the local FRED cache:

```powershell
.venv/Scripts/python.exe -m scripts.economy --as-of 2026-11-07 --customer C002
```

See `customer_pressure.conditions` in `artifacts/reports/economic-outlook.json`. To feed an indicator report to a financial forecast, align its date with the customer snapshot. The bundled PNC customer snapshots end October 31:

```powershell
.venv/Scripts/python.exe -m scripts.economy --as-of 2026-10-31 --customer C002
.venv/Scripts/python.exe -m scripts.run forecast --customer C002 --all-horizons --indicators artifacts/reports/economic-outlook.json
```

That historical demonstration uses revised data, not a point-in-time backtest. Future-dated snapshots are rejected by analysis. Member 2 should supply publication-aware snapshots for production and deliver/deduplicate alerts. No notifications or account actions are executed here.

## Financial reasoning sources

The [CFPB emergency-fund guide](https://www.consumerfinance.gov/an-essential-guide-to-building-an-emergency-fund/) explains reserves for unexpected expenses and notes that the appropriate amount depends on personal circumstances. [Investor.gov](https://www.investor.gov/introduction-investing/getting-started/asset-allocation) explains the role of investing horizon and risk tolerance in allocation. The [CFPB's fixed/adjustable mortgage explanation](https://www.consumerfinance.gov/ask-cfpb/what-is-the-difference-between-a-fixed-rate-and-adjustable-rate-mortgage-arm-loan-en-100/) distinguishes contract rate behavior. These support the qualitative reasoning, not FinPilot's numerical thresholds or classifier validity.
