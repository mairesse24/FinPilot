# Financial score validation

Executed full suite: 195 passed, 1 skipped, 0 failed.

The property loop checks 200 reproducible input combinations (seed 42).
These test mathematical consistency and safety, not score accuracy against an
invented ground truth. Explicit invariants cover 0–100 bounds, finite JSON,
missing inputs, monotonic savings/essential/debt effects, small perturbations,
net-worth conservation for transfers and principal repayment, cash-only repayment
settlement, missing credit limits, no automatic fixed-debt repricing, no market
markdown of checking, deterministic repeated inputs and macro-independent health.
Temporal tests reject future releases, stale data and unverified historical Yahoo.
Mock HTTP tests cover bounded retries/redaction. Live FRED/Yahoo results and
historical replay are separate from mocked provider tests. No paid LLM call is
used to validate financial arithmetic.

Representative **synthetic** profiles with declared assumptions:

| profile | score | completeness | Emergency preparedness | Cash-flow sustainability | Debt-payment affordability | Payment readiness | emergency_months | monthly_surplus | credit_utilization | income_monthly_cv |
|---|---|---|---|---|---|---|---|---|---|---|
| base | 67.4700 | 1.0000 | 5.2600 | 64.6200 | 100.0000 | 100.0000 | 0.3158 | 1900.0000 | N/A | N/A |
| high_income_high_debt | 35.0700 | 1.0000 | 0.0000 | 59.1100 | 50.0000 | 31.1700 | 0.0000 | 3700.0000 | N/A | N/A |
| low_income_strong_savings | 91.1300 | 1.0000 | 100.0000 | 64.5200 | 100.0000 | 100.0000 | 12.0000 | 900.0000 | N/A | N/A |
| high_income_no_emergency_savings | 70.9800 | 1.0000 | 0.0000 | 83.9200 | 100.0000 | 100.0000 | 0.0000 | 9700.0000 | N/A | N/A |
| low_income_manageable | 68.6300 | 1.0000 | 10.0000 | 64.5200 | 100.0000 | 100.0000 | 0.6000 | 900.0000 | N/A | N/A |
| irregular_income_large_reserves | 91.1600 | 1.0000 | 100.0000 | 64.6200 | 100.0000 | 100.0000 | 6.3158 | 1900.0000 | N/A | 0.8296 |
| high_card_utilization | 66.5600 | 1.0000 | 5.0000 | 63.6400 | 97.6200 | 100.0000 | 0.3000 | 1800.0000 | 0.9000 | N/A |
| strong_savings_poor_payment_timing | 64.5900 | 1.0000 | 90.7900 | 64.6200 | 100.0000 | 2.9400 | 5.4474 | 1900.0000 | N/A | N/A |
| negative_cash_flow | 61.1800 | 1.0000 | 5.2600 | 39.4700 | 100.0000 | 100.0000 | 0.3158 | -800.0000 | N/A | N/A |
| missing_financial_inputs | N/A | 0.0000 | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| confirmed_zero_income | N/A | 0.7500 | 5.2600 | 0.0000 | N/A | 100.0000 | 0.3158 | -2300.0000 | N/A | N/A |

One-factor sensitivity (debt perturbations use a $200 debt-payment baseline):

| input | factor | score | change | Emergency preparedness | Cash-flow sustainability | Debt-payment affordability | Payment readiness |
|---|---|---|---|---|---|---|---|
| savings | 1.1000 | 67.6000 | 0.1300 | 5.7900 | 64.6200 | 100.0000 | 100.0000 |
| savings | 1.2500 | 67.8000 | 0.3300 | 6.5800 | 64.6200 | 100.0000 | 100.0000 |
| savings | 1.5000 | 68.1300 | 0.6600 | 7.8900 | 64.6200 | 100.0000 | 100.0000 |
| income | 0.9000 | 66.8600 | -0.6100 | 5.2600 | 62.1700 | 100.0000 | 100.0000 |
| income | 0.8000 | 66.1600 | -1.3100 | 5.2600 | 59.3600 | 100.0000 | 100.0000 |
| income | 0.7000 | 65.3400 | -2.1300 | 5.2600 | 56.1100 | 100.0000 | 100.0000 |
| essential | 1.1000 | 66.8900 | -0.5800 | 4.7800 | 62.7800 | 100.0000 | 100.0000 |
| essential | 1.2000 | 66.3600 | -1.1100 | 4.3900 | 61.0500 | 100.0000 | 100.0000 |
| debt | 1.1000 | 65.5000 | -0.1700 | 4.7200 | 62.5000 | 94.7600 | 100.0000 |
| debt | 1.2500 | 65.2300 | -0.4400 | 4.6500 | 62.2200 | 94.0500 | 100.0000 |
| checking | 0.1000 | 44.6900 | -22.7800 | 0.0000 | 64.6200 | 100.0000 | 14.1200 |
| checking | 0.5000 | 59.0200 | -8.4500 | 0.8800 | 64.6200 | 100.0000 | 70.5900 |
| checking | 1.5000 | 67.4700 | 0.0000 | 5.2600 | 64.6200 | 100.0000 | 100.0000 |

Weight changes of ±5 percentage points produced total-score changes ranging
from -4.7320 to 4.7320 points across these
profiles. Full alternatives are in `weight_sensitivity.csv`. This material
sensitivity is another reason to label the weights provisional, not scientifically
optimal. Missing scores are intentionally withheld, not NaN API values.

Limitations: confirmed inputs can still be inaccurate user statements; source
coverage is limited to imported accounts; no validated well-being outcome labels;
no official CFPB questionnaire equivalence; imperfect bill completeness; no
restricted-fund knowledge without confirmation; no full historical savings-rate
ledger; calendar-month income CV includes pay-frequency effects and is not scored.
Historical score-change attribution requires stored historical assessments, which
are not yet persisted; the UI instead explains current formulas and explicit
before/after scenario changes. No retroactive score history is invented.

Reproduce with `python -m scripts.validate_financial_score`, `python -m pytest`,
and `python -m scripts.document_economic_engine`. API integration uses scoped
profiles, confirmed facts and deterministic stress responses. Existing v1 score
endpoint remains unchanged and is explicitly labeled legacy in the UI/chat.
