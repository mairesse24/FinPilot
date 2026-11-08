# Economic experiments and reserve alerts

Two separate tasks are implemented. Neither assumes economic indicators reliably predict the stock market.

## Household economic outlook

Ridge regression estimates the next calendar month's national CPI year-over-year inflation and unemployment rates. Features include two-month-lagged macro levels/changes and observed month-end market returns. Expanding-window evaluation compares final 24 eligible target months against persistence of the lagged observation. Training excludes labels that would not yet have been released under the conservative two-month assumption.

The initial run did not beat persistence: inflation MAE 0.5080 percentage points versus 0.4655; unemployment MAE 0.5698 versus 0.1000. Both remain research estimates; the output recommends displaying the persistence baseline until point-in-time validation. Observed economic pressure and clearly labeled cost-of-living scenarios can be used independently of these unsuccessful regressions.

## S&P 500 direction research

Logistic regression predicts whether the next calendar month's S&P 500 price return is positive. It is separate from the household model and excludes dividends. Expanding evaluation compares historical positive-return frequency and a three-month momentum rule, using balanced accuracy and Brier score. The first run produced balanced accuracy 0.5000 and Brier 0.3016 versus historical-prior Brier 0.2843; it failed the baseline gates. `direction` is `abstain`, not an up/down claim. The model's uncalibrated probability is retained solely for research inspection.

## Data and reproducibility

```powershell
.venv/Scripts/python.exe -m scripts.fetch_economy
.venv/Scripts/python.exe -m scripts.economy --as-of 2026-11-07 --customer C002
```

The explicit downloader obtains public FRED CSVs and records fetch time, source URLs and last observation dates in `data/economy/provenance.json`. Raw `data/economy/fred.csv` is ignored by Git; do not distribute third-party raw histories without reviewing source terms. The report is `artifacts/reports/economic-outlook.json`. No LLM or FRED API key is required. This evaluates algorithms on each invocation; no separate economic serving artifact is deployed yet.

Sources:

- [CPIAUCSL](https://fred.stlouisfed.org/series/CPIAUCSL): monthly seasonally adjusted CPI index; inflation calculated using the same calendar month one year earlier.
- [UNRATE](https://fred.stlouisfed.org/series/UNRATE): monthly seasonally adjusted unemployment percentage.
- [FEDFUNDS](https://fred.stlouisfed.org/series/FEDFUNDS): monthly federal funds effective rate, percentage points.
- [SP500](https://fred.stlouisfed.org/series/SP500): daily price index; last trading observation used for each complete calendar month. FRED's notes describe limited daily history and copyright terms.

Public current-vintage downloads are revised histories. Lagging observations does not remove revision leakage. [FRED real-time periods](https://fred.stlouisfed.org/docs/api/fred/realtime_period.html) explains the distinction between what is known today and what was known historically. Production validation needs ALFRED vintages or stored publication-time snapshots, more evaluation origins, calibration and a separate final holdout. Current macro data is not a forecast of an individual's job or income.

## Savings-floor notifications

```powershell
.venv/Scripts/python.exe -m scripts.run forecast --customer C002 --all-horizons --savings-floor 1000 --fund-shortfalls-from-savings
```

This enables an explicit hypothetical policy: use available savings to cover projected negative checking. Without it, savings is not silently depleted by spending. Guardian creates a dated `savings_below_floor` event when the reserve threshold is crossed. Alert objects include a stable deduplication key; actual delivery/persistence belongs to Member 2. C002 may not breach a $1,000 floor because its synthetic reserves are large. The regression tests independently verify a customer with $100 checking, $500 savings and $200 spending: checking becomes $0, savings $400, and a $450 floor triggers next-day notification evidence.

## Why the daily spending looks periodic

The PNC generator puts housing/utilities on the 3rd/10th, variable checking spending on the 18th/25th and card purchases on the 4th/11th/19th/25th. C002 has about 83% zero variable-spending days. Learned zero days and repeated amounts reflect this artificial schedule, not validated real-world behavior.

The updated model includes previous-calendar-month spending and trailing three-calendar-month same-day averages, plus a calendar-month baseline. Reports now include spending-day errors and cumulative horizon bias. Small all-day MAE is insufficient evidence because zeros dominate; the calendar baseline still wins for some customers/horizons. Do not smooth the daily path and present that as improved accuracy. Production work needs realistic event timing, per-category behavior and broader held-out histories.
