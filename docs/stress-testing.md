# CSV stress suite

Run `.venv/Scripts/python.exe -m scripts.stress_test` from the project root. No chatbot keys or credits are needed. Use the README setup on a fresh checkout to obtain the trained artifacts and FRED cache first.

Inputs: `data/synthetic/stress-cases.csv`. Edit the numeric values, required/forbidden alert IDs or expected condition labels to add cases. `scripts.generate_stress_cases` restores the original 52-case CSV and overwrites edits; rerunning the stress runner preserves edits.

Outputs under `artifacts/reports/`:

- `stress-results.csv`: status, labels, alerts, forecast spending, balances, model sensitivities and validation errors.
- `stress-results.md`: readable case table, guidance and actual scenario effects.
- `stress-results.json`: complete analyses, daily paths, numeric evidence and research-model responses.

## What actually runs

| Engine | Code exercised | Meaning of PASS |
| --- | --- | --- |
| controlled | Known daily scenario spending, cash calculations, observed-condition rules, Guardian and simulations | Declared alert/no-alert and boundary expectations match |
| ml | Three saved LightGBM quantile models, or a labeled baseline fallback, followed by financial analysis | Output contracts/validation hold; sensitivity is recorded, not claimed accurate |
| research | Inflation Ridge, unemployment Ridge and S&P-direction logistic regression refitted on modified cached histories | Outputs are finite, short history is rejected and unvalidated directional signals still abstain |

There are three saved quantile regressors for one spending task, two macro regressions and one equity-direction research classifier. The observed market/economy classifiers used for alerts are transparent rules, not additional trained predictive models.

The cases cover overspending, future budget overruns, exact boundaries, short forecast windows, low cash, reserve withdrawals, zero income, high inflation, unemployment changes, interest-rate exposure, fixed versus variable debt, near-term versus long-term equity holdings, debt/liquidity tradeoffs, stale/future/missing observations, malformed financial inputs, all three forecast horizons, irregular/zero/surging spending, one-off spikes, malformed ML histories and extreme economic-history shocks. The required and forbidden outputs are declared independently in the CSV.

Each offered scenario is actually executed, and its ending/minimum checking changes are recorded. A rate or income shock can worsen balances; it is a scenario to inspect, not an improvement recommendation. The 7/30-day ML paths are also checked against the corresponding prefix of the 90-day path.

## Findings and fixes

1. **Missing forecast-budget alert:** the first 45-case run had one failure. Historical overspending worked, but a complete future month with $3,000 spending against a $1,000 budget produced no forecast alert. Added `projected_spending_above_budget`: full-calendar-month forecast total >120% of the supplied variable budget. It reports month total, overshoot and first threshold-crossing date. A seven-day slice alone does not establish a whole-month overrun.
2. **Irregular-history underprediction:** original LightGBM output was about $16 across 90 days despite recent activity averaging about $31/day. The synthetic calendar pattern did not generalize. Training now records zero-day frequency; sufficiently long histories with much more frequent spending use a rolling-average fallback and explicit warning. This guard and fallback are heuristics, not validated real-world prediction methods.
3. **Scenario rounding:** a $200 monthly cut across 30 days previously became $200.10 due to daily rounding. Monthly scenario totals now reconcile cents to the requested prorated amount, with an exact regression test.
4. **Unreliable research extrapolation:** the modified equity-crash history produced an uncalibrated up-probability near 0.85 and large macro forecast shifts. Those are sensitivity findings, not usable financial forecasts. The research classifier continues to abstain; observed-condition rules drive alerts.

The rate case verifies approximate additional interest of $10/month for a hypothetical one-percentage-point shock on $12,000 variable debt. It is not a lender payment quote. Market cases verify review guidance for near-term equity cash needs without a blanket sell or spending-cut instruction for long-term holders.

## Limits

Passing the suite means specified software behavior is satisfied, not 100% predictive accuracy. Irregular/surge cases have no future spending ground truth. ML cases use C026's history with explicitly fictional financial snapshots. Research transformations alter historical data; they are not unseen real outcomes and are never represented as observed FRED history. Forecast accuracy and vintage limitations remain in `model-card.md` and `economic-research.md`. This suite produces app-ready alert objects, not external notification delivery.
