# FinPilot prototype model card

## Reliability update

Dashboard warning investigation: [WARNING_RELIABILITY_REPORT.md](WARNING_RELIABILITY_REPORT.md).
Runtime quality routing now avoids calendar-trained LightGBM for fewer than 90
observed history days, where the frequency support check cannot run. Backend uses
the observed-history baseline; dictionary forecasts use rolling-28. Both remain
unvalidated and disclose uncertainty. Existing >=90-day frequency safeguard and
model weights remain unchanged. This is conservative eligibility routing, not a
claim of improved accuracy. A single historical synthetic Nessie block and existing
separate synthetic calibration comparisons do not validate real-customer outcomes.

The original training/point-forecast results below remain historical measurements.
See [BEFORE_AFTER_EVALUATION.md](../BEFORE_AFTER_EVALUATION.md) for the executed
reliability evaluation and immutable baseline snapshot. Trained model weights,
feature schema and source final-test records remain unchanged.

Checking projections now distinguish consumption from card settlement, use
origin-only per-payday/bill estimates in the PNC adapter, and represent recurring
signed external movements separately from income and spending. These movements
are inferred from past months and may not recur. Generic backend forecasts exclude
card purchases from checking-spending history; scheduled repayments remain cash
outflows. Unlinked debt obligations are disclosed as an aggregate floor.

Cold-start fallback uses observed days only, with an explicit limited-history
warning; absent/short-zero history abstains. This is not proof of forecast accuracy.
Posthoc residual bands are fitted on separate calibration data, targeted at 80%
positive-spending coverage. They are model-hash bound, empirically evaluated and
not universally calibrated 80% intervals. Frequent-spending coverage remains below
target. Model-file changes invalidate the calibration policy until it is refitted.

## Data and target

PNC synthetic account history: 30 fictional customers, 24 months (2024-11-01 through 2026-10-31), 21,225 ledger entries. Daily target sums `expense` entries in groceries, transport, dining, shopping and other_spending. Missing daily activity is explicitly zero. Housing and utilities become scheduled bills. Internal transfers, external calibration transfers and noncash interest are excluded from the ML target. Credit-card consumption is counted once, not counted again as card repayment. This approximates cash timing of new card spending; it is not an exact statement-payment forecast.

Features: shifted lags 1/7/28 days; shifted rolling 7/28-day mean and 28-day standard deviation; previous-calendar-month same-day spending and trailing three-calendar-month same-day mean; day of month, weekday, month and approximate semi-monthly payday distance. Calendar features fall back to the prior 28-day average when history is unavailable. No customer ID, final balance, future transactions or target-day spending enters the feature matrix. Per-category histories and customer-specific payday features remain future improvements.

## Training and evaluation

LightGBM quantile regressors at 0.1/0.5/0.9, fixed seed 42, early stopping on validation. Dates before 2026-04-04 are training, dates through 2026-07-17 validation, remaining dates test. C025–C030 are excluded from training and validation entirely. Serving point model is chosen from median LightGBM, 28-day average, lag-7 and previous calendar month using validation MAE only.

Measured local results:

| Period | LightGBM daily MAE | 28-day average MAE | Lag-7 MAE | Calendar-month MAE |
| --- | ---: | ---: | ---: | ---: |
| Chronological test | $2.62 | $169.38 | $102.47 | $3.63 |
| Held-out customer test | $3.04 | $162.36 | $98.15 | $2.87 |

These are one-day walk-forward results with known prior observations. See `artifacts/reports/training.json` for row counts, intervals and exact split dates. Synthetic spending occurs on highly predictable dates; these numbers are not evidence of real customer accuracy. Many zero-spending days reduce aggregate daily MAE. The 10th/90th intervals covered about 95.7% of test observations, rather than nominal 80%, reflecting discreteness and lack of calibration. The calendar-month baseline beats LightGBM on the held-out customer test; do not claim universal superiority.

`scripts.backtest` additionally evaluates recursive 7/30/90-day predictions for C001, C002, C025 and C026 at 2026-07-19 and 2026-08-02. No future actual spending enters recursive features. Read `artifacts/reports/recursive-backtest.json` for all-day and spending-day MAE, calendar-month baseline and cumulative spending errors. Only two overlapping origins and four customers are checked; their errors are not independent. Broader rolling-origin validation, calibration, category-level errors and realistic irregular-income tests remain necessary before broader use.

## Financial assumptions and limits

- Checking is the spendable cash projection. Savings is included in emergency coverage but is never automatically swept to checking.
- An explicit `fund_shortfalls_from_savings` option can model hypothetical reserve withdrawals, capped by savings available. `savings_floor` produces dated app-alert candidates; no actual transfer or external notification is performed. Central-case transfer amounts are also applied to displayed stress envelopes, so those bounds are not separate funded-reserve simulations.
- Income repeats at normalized paydays; bills repeat monthly. Historical bill schedules are estimates; real schedules should come from Member 2.
- Account snapshot income/payment assumptions can differ from generated ledger history. Artificial external cash transfers are deliberately excluded.
- Health score uses the proposal weights 25/25/20/15/15. Formulas are returned with each component. Stability is presently a surplus proxy; emergency coverage conservatively uses all outflows. Readiness considers one full month of bills, not a due-date-specific affordability score.
- Unknown budget, undefined zero-income ratios and undefined expense coverage are omitted with weights renormalized.
- Guardian thresholds (buffer, three months reserves, 36% debt/income, 20% budget overrun) are internal demo assumptions. Actions are scenarios to explore, not guaranteed improvements; saving or extra debt payment can worsen checking liquidity.
- Quantiles are sorted to handle crossing and widened to include the chosen baseline point if necessary. Recursive quantile ranges do not propagate lag uncertainty. Summed cash bounds are stress envelopes, not calibrated prediction intervals.
- The LightGBM point path uses daily conditional medians. Their sum is a planning total, not an expected spending total or a calibrated median of cumulative spending.
- A training-derived zero-day frequency profile now checks histories of at least 90 days. Histories more than 0.15 below the minimum training zero-day fraction use a labeled rolling-average fallback and volatility-based stress bounds. This heuristic followed severe irregular-history underprediction in the CSV stress suite; it is not a validated distribution-shift detector or new real-world accuracy claim. Shorter histories warn that this check is unavailable.
- Simulations scale forecast paths, not retrain the model. They omit taxes, irregular bill schedules, loan amortization and future interest savings.
- Economic index is a transparent generic stress heuristic, not a causal personal-risk model. A supplied snapshot can be stale; backend ingestion should label observation dates.
- Copilot has approved calculation-only tools, bounded rounds, no transaction tools and a numeric-token audit. Numeric matching cannot validate the meaning of prose. Live API integration has fake-client tests only; paid calls were not made.

For real deployment, add broader validation, auth, structured-output evaluation, production data monitoring, interval calibration and exact monetary accounting with the backend team.
