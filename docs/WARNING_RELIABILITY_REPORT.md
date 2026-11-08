# Dashboard warning and forecast reliability investigation

Date: 2026-11-07. Product: FinPilot. The work preserves the distribution-shift
safeguard, original trained weights, original final-test records and score formulas.

## Root causes and financial implications

| Message | Exact origin and trigger | Financial interpretation | Change |
| --- | --- | --- | --- |
| Frequent spending / rolling fallback | `backend/intelligence/forecasting.py::forecast_spending`: at least 90 observed days and recent zero-day fraction below training minimum minus 0.15. | Genuine mismatch with the synthetic calendar target; the detector is a heuristic, not a validated statistical shift test. Baseline spending is an uncertain assumption, not a demonstrated accurate forecast. | Detection retained. One friendly critical notice, complete diagnostic, explicit method/status/validation/reasons. |
| Nessie sandbox snapshot | `backend/app/data/nessie.py::import_customer`, `build_nessie_repo`: banking records imported at process startup. `/api/context` returns `loaded_at`. | Account balances are saved authoritative sandbox snapshots; analysis reload does not fetch new banking records. | Timestamp retained, one data limitation, browser/API cache disabled. No implicit refresh or fabricated current balance. Restart API to re-import. |
| Database demo substitution | `backend/app/db/factory.py::build_repo`: configured PostgreSQL cannot be used and generated records are substituted. | These are a different dataset, not the configured financial records. | Explicit critical `data_source_substituted` notice; never hidden as a technical-only warning. |
| Loan principal policy | `import_customer`: original loan amount is not a remaining balance. | Correct accounting policy; inventing outstanding debt from original principal would be wrong. | General policy moved to engineering diagnostics. |
| Missing approved-loan balance | `import_customer`: approved loan lacks explicit `loan_balances` entry. | Loan omitted: displayed liabilities can be understated and net worth overstated. Arithmetic over imported accounts is correct, but incomplete totals are not a complete financial picture. | Critical visible notice retained; regression coverage preserves omission rather than guessing. |
| Loan dates | `import_customer`: confirmed principal but no explicitly linked payment calendar. | Monthly payment alone cannot establish due dates. | Notice emitted only when no linked bill exists; one user-friendly data limitation. |
| Unverified deposits | `import_customer`: imported positive checking deposits with category `income`. | Actual cash received is not proof of earned salary or future recurring income. Forecast income still comes from explicit schedules. | Conditional notice only when applicable. Explicit refund mappings supported and excluded from income metrics. |
| Purchase classification / cash scope | `import_customer`: unmapped purchases are `other`; transfers endpoint omitted, card/savings activity and withdrawals excluded. `_history` uses `metrics.checking_variable_transactions`. | Correct exclusion avoids double counting card purchases and settlements; cash consumption is unobserved. Unclassified historical bills may still be counted as variable spending. | Separate scoped limitations; no fabricated categories or auto-matching by amount/date. Regression tests cover fixed bills, transfers, cards, withdrawals and refunds. |
| Member 3 prototype score | `backend/intelligence/backend_adapter.py::health_profile`: legacy health score excludes unavailable components and normalizes remaining weights. `_customer` supplies no budget, so spending discipline is unavailable. | Original methodology is a heuristic, not a credit score or validated wellness instrument. Missing-factor normalization can make scores incomparable across coverage levels. | Internal team terminology removed. Data limitation explains excluded factors and adjusted weights. No formula/weight changes. V2 remains separately versioned and withholds incomplete totals. |
| Unlinked debt overlap | `_meta`, `app/services/health.py::get_health`: unlinked debt bills coexist with minimum payments. | Existing aggregate floor prevents straightforward duplicated debt burden but lacks exact attribution. | Stable `debt_linkage_incomplete` notice, explanatory text, technical attribution instructions preserved. |
| Insufficient history / abstention | `app/baseline/forecast.py::forecast`, `_daily_variable`; `forecast_profile`. | Missing history must not be represented as zero future spending. | Short histories use observed-history baseline; absent or short all-zero histories abstain. Unavailable Digital Twin cash values/deltas now null, not $0. |

### Propagation before this change

`forecast_spending.warnings -> backend_adapter._project.meta.warning ->
services.forecast.get_forecast -> services.guardian.get_guardian ->
services.dashboard.build_dashboard.meta.warning`.

Guardian concatenated the forecast string; dashboard concatenated Guardian and
health strings. Text-based deduplication only compared whole strings, so partially
overlapping compound strings survived. `ConnectedDashboard.tsx` printed context
warnings, dashboard warning and forecast warning separately. Limited-history
Guardian cards also repeated the uncertainty warning.

`Gateway.make_meta` reconstructed metadata; new structured information needed
explicit preservation through this seam. This is now covered end to end.

## Actual dataset comparison

Read-only live import of the configured fictional Nessie customer; no banking
records were written. Artifacts contain aggregates, not credentials or customer IDs.

| Measure | Training period, fitted customers | Configured Nessie snapshot |
| --- | ---: | ---: |
| Customers | 24 | 1 |
| Calendar history | 519 days/customer; 12,456 pooled days | 120 days |
| Variable purchase transactions | 2,520 | 40 |
| Transactions per customer-day | 0.2023 | 0.3333 |
| Zero-spending days | 83.04% | 66.67% |
| Positive spending days | 16.96% | 33.33% |
| Mean positive-day spending | $558.92 | $59.00 |
| Mean daily spending | $94.77 | $19.67 |
| Daily spending p95 | $643.25 | $112.00 |

Training comparison uses dates before 2026-04-04 and excludes C025-C030. This
aggregate training-period zero fraction differs slightly from the serialized
serving profile (0.83299389). The actual serving threshold is
`0.83299389 - 0.15 = 0.68299389`; Nessie's `0.66666667` triggers it.
The decision depends on days with spending, not a count of purchases within a day.

Nessie has 40 `other` purchases totaling $2,360 and 8 imported inflows. All its
variable purchase dollars are uncategorized. Training variable dollars are split
among groceries, transport, dining, shopping and other_spending; exact shares are
in `data_comparison.json`. Training consumption can include card purchases, whereas
this backend checks checking-only cash spending. Targets are therefore not fully
equivalent even if names are mapped.

**Conclusion:** there is an observed frequency and amount shift. Known exclusion
logic is not including transfers, withdrawals or card consumption in this forecast
target. No evidence establishes that the uncategorized purchases are bill payments
or refunds; the import cannot prove category completeness. Explicit mappings fix
known classifications; automatic relabeling would invent facts. The frequency
detector also cannot detect every possible shift or establish account-history
coverage. Zero reindexing presumes records between the first event and snapshot
are complete; that remains a data-quality limitation.

## Actual forecast comparison and serving decisions

One available Nessie origin, 2026-10-08, has 90 prior history days and a complete
30-day later *synthetic recorded-purchase* block. Future actual values were excluded
from features; recursive baselines feed only their own previous predictions.

| Method | 7-day daily MAE | 7-day total error | 30-day daily MAE | 30-day total error |
| --- | ---: | ---: | ---: | ---: |
| Existing recursive rolling-28 fallback | $22.31 | +$0.69 | $26.08 | -$13.72 |
| Fixed trailing 28-day mean | $22.39 | +$1.00 | $26.24 | +$1.43 |
| Calendar-average recursion | $23.72 | -$3.99 | $30.01 | +$21.00 |
| Previous-week recursion | $42.14 | +$21.00 | $38.87 | +$154.00 |
| Rolling-30 recursion | $21.95 | -$0.67 | $25.63 | -$13.17 |

Actual totals: $137 over 7 days and $590 over 30 days. Small total error can coexist
with large daily errors because errors cancel. Horizons overlap; there is only one
customer/origin. Cash-balance errors cannot be measured from incomplete movement
history and a current balance alone. **The fallback remains unvalidated for real
customer use.** No statistical significance claim is supportable here; the modest
MAE difference between 28- and 30-day rolling forecasts is not grounds to switch.

Existing, separately generated independent **calibration** profiles (seed 20261001,
30 profiles/group, 30 future days each) provide additional synthetic evidence:

| Calibration group | LightGBM daily MAE | Rolling-30 daily MAE | Paired difference: LightGBM minus rolling-30, customer bootstrap 95% |
| --- | ---: | ---: | --- |
| Frequent spending | $55.68 | $43.33 | +$12.35 [$6.64, $18.42] |
| Irregular sparse spending | $20.14 | $28.53 | -$8.39 [-$10.93, -$5.93] |

These are synthetic generator-specific comparisons, not real-world confidence
intervals or forecasts. Bootstrap resamples customers (2,000 replicates, seed 42).
They support retaining frequency-specific safeguards rather than routing every
customer to one baseline. Production fallback is rolling-28, not the rolling-30
comparator. No final-test outcomes were used to select a model/threshold.

Serving policy:

1. Missing history or fewer than 29 days with no positive spending: abstain.
2. Backend history below 90 days: use the existing observed-mean/weekday baseline,
   label unvalidated; below 29 days retain `limited_history`. Calendar support is
   unavailable, so do not silently serve LightGBM. Core dictionary forecasts also
   use rolling-28 below 90 days, with the support-check limitation.
3. At least 90 days and existing frequency safeguard triggers: retain rolling-28
   and limited-confidence notice. No threshold fitted from new Nessie outcomes.
4. Supported history: preserve existing validation-selected point model. Model
   evidence is synthetic-only, not a transferable real-customer accuracy claim.

The short-history routing is a conservative data-quality gate, not a proven accuracy
improvement. Fitting, feature schema, quantile weights and calibration policy remain
unchanged. Existing fixed-origin recursive 7/30/90-day backtest was executed again;
24 results are under `artifacts/reports/recursive-backtest.json`. No model was
retrained. A broader realistic labeled cohort is still needed before changing
validated model-selection policy or declaring Nessie forecasts reliable.

## New notice and reliability contract

`Meta.notices[]` and `/api/context.notices[]` expose:

```json
{
  "code": "forecast_pattern_shift",
  "context": "analysis",
  "category": "critical",
  "message": "Your recent spending pattern differs from the model's training data, so we're using a simpler estimate. Forecast confidence is limited.",
  "technical_detail": "Full original diagnostic retained here"
}
```

- Critical reliability warnings: visible once, including unavailable forecasts,
  unvalidated fallback, missing loan principal and missing income/bill schedules.
- Data limitations: one expandable plain-language list, including partial legacy
  scores, unverified deposits, purchase/card/cash scope and snapshot behavior.
- Diagnostics: expandable technical details; unknown engineering strings are not
  shown as raw user-facing messages. Gateway failures retain backend logs.

`app/services/notices.py` is the compatibility mapping for existing warning text;
new provider-native codes are a future improvement. `merge_notices` and frontend
`uniqueNotices` use `(code, context)`, not whole compound strings. Context distinguishes
bank data from analysis; the current screen is scoped to one selected customer.
Technical payloads remain available without duplicate identical detail blocks.
Legacy `warning`/`warnings` fields remain for API compatibility, not primary UI.

`Meta.forecast_reliability` carries method, status, validation, reasons, support
check and explicit interval limitation. Forecast -> Guardian -> dashboard and both
simulation outcomes preserve it, as do chatbot tools. Missing forecast cash values
are null. Legacy health is **not** forecast-based (`forecast_reliability=null`);
v2 assessments and confirmed-budget economic simulations explicitly declare no ML
forecast dependency and carry bank-data notices. They do not inherit an invented
forecast confidence. Wrapped now consumes the live dashboard/forecast presentation
instead of the static sample recap; no swipe/narration implementation is claimed.

Financial low-balance, payment and reserve alerts remain. The redundant Guardian
`forecast_uncertain` card is represented by the common reliability notice in the UI;
it remains in programmatic Guardian responses. Forecast risk banners avoid repeating
an already displayed low-balance alert. Bank snapshot age is displayed. API responses
use `Cache-Control: no-store`; browser requests use `cache: no-store`. Aborted request
results cannot replace a newer horizon or reload. No response cache was found in the
financial services; startup snapshot persistence is deliberate, not a cache bug.

## Validation and before/after results

| Check | Before | After |
| --- | --- | --- |
| Full Python suite | 195 passed, 1 skipped | 204 passed, 1 skipped |
| New regression coverage | No structured notice/metadata tests; first run failed import for missing notice service | Stable scoped codes, deduplication, missing loan/deposit notices, forecast/Guardian/dashboard/tool/simulation propagation, short history, normal vs shifted history, no-store headers, unknown cash values and importer exclusions covered |
| Existing empty-profile simulation assertion | Expected invented $0 cash delta | Updated to require unavailable balance/cash delta; score delta remains independently computable |
| Required intelligence check | Prior task 70 passed | 70 passed in this task; overlaps full suite |
| Browser verification | No fresh pre-change browser measurement | 7 passed, including warning deduplication/diagnostics and live Wrapped route |
| TypeScript and production build | Not remeasured before edits | Both passed |

The first browser run had 6 passes and a cold-start timeout while the dashboard
was still loading. The abstention test now awaits its actual dashboard dependency
before asserting, rather than racing a five-second UI assertion against model
imports. Financial assertions remain intact; the full seven-test rerun passed.
Python still emits an upstream Starlette/httpx deprecation warning, unrelated to
financial reliability. No paid LLM calls or real-customer outcomes were tested.

Reproduction artifacts: `reports/warning_reliability/before-tests.xml`,
`after-tests.xml`, `data_comparison.json`, `nessie_historical_spending.csv`,
`existing_calibration_comparison.csv`, `calibration_comparison_uncertainty.json`.
Run `python -m scripts.investigate_warnings` for a fresh read-only sandbox comparison;
it overwrites the aggregate snapshot report, so preserve previous evidence first
when comparing changing banking records. Run full tests and required checks as in
`AGENTS.md`. No gains in predictive accuracy or real-world calibration are claimed.
