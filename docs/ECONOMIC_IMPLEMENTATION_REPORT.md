# Economic intelligence implementation report

Implemented on 2026-11-07. This report covers the additive economic and financial
v2 work; existing uncommitted forecasting reliability work is preserved.

## Implemented behavior

| Layer | Implementation | Behavior |
| --- | --- | --- |
| Ingestion | `backend/intelligence/economic_data.py` | Official FRED/ALFRED vintage queries, retry/redaction, dated local snapshots; Yahoo adjusted market history, freshness checks and explicit failures. |
| Features and regimes | `backend/intelligence/regimes.py` | Inflation, labor, growth, monetary/credit and market dimensions; conflicting signals coexist. No predictive probability or invented accuracy. |
| Personal score | `backend/intelligence/personal_finance.py` | Four equally weighted, provisional v2 components with formulas, missingness, confirmed budgets and debt/calendar safeguards. Original v1 is preserved. |
| Resilience and simulation | `backend/intelligence/resilience.py` | Personal exposure rules and deterministic 30-day scenarios, separate from macro classification and ML forecasts. Transfers and principal repayment conserve net worth. |
| Integration | `backend/app/services/economic_intelligence.py`, `backend/app/routes/economic_intelligence.py`, `backend/app/tools/registry.py` | Scoped API and chatbot tools. No tool can select another customer or execute a bank transaction. |
| UI | `frontend/src/EconomicIntelligence.tsx` | Economic Lab, Health Score, Digital Twin and Copilot use actual backend responses, dates, missing-input states and before/after charts. |

Available scenarios include essential-cost or all non-debt cash-expense increases,
income reduction/interruption, one missed paycheck, delayed pay schedules, emergency
expenses, explicit extra variable-rate payments, fixed-bill increases, savings
transfers and principal repayment. Percentage, amount and delay assumptions must
be explicit. Principal repayment requires an owned liability identifier. The UI
exposes the common scenarios; liability-specific repayment is API-supported.

## Actual evidence

- Live refresh retrieved 16 FRED and 8 Yahoo series with zero provider errors.
  Raw snapshots stay local under ignored `data/economic_snapshots/`.
- Six historical FRED vintage replays executed: 2008-10-31, 2009-03-31,
  2020-04-30, 2022-06-30, 2023-07-31 and 2017-06-30. Unavailable historical
  series remain unavailable. Yahoo current revised history is excluded.
- Full Python suite: **195 passed, 1 skipped**. Required `scripts/check.ps1`:
  **70 passed**. These overlap and must not be added together.
- Frontend TypeScript check and production build passed. Headless Edge integration:
  **6 passed in 28.4 seconds**, one worker, local API using the existing fictional
  Nessie customer and actual cached macro observations. A preceding two-worker run
  concurrent with Python evaluation had two five-second assertion timeouts while
  responses were still loading (4 passed, 2 failed). No assertions were weakened;
  the sequential rerun passed all six. This is not a load-test result.
- `pip check` found no broken requirements. Frozen lower/median/upper LightGBM
  hashes match the pre-existing evaluation baseline: no model retraining.
- Eleven financial profiles, input/weight sensitivities and historical replay
  artifacts are in `reports/economic_intelligence/`. These test arithmetic and
  behavior; they do not validate a financial-well-being outcome or market prediction.

## Run and inspect

Keep `FRED_API_KEY` privately in root `.env`, then refresh deliberately:

```powershell
.venv/Scripts/python.exe -m scripts.refresh_intelligence --as-of 2026-11-07
.venv/Scripts/python.exe -m uvicorn app.main:app --app-dir backend --reload
```

In another terminal:

```powershell
cd frontend
npm.cmd run dev
```

Open the displayed Vite URL and choose **Economic Lab** or **Health Score**.
Enter confirmed monthly budgets, debt obligations and accessible savings; confirm
bill/debt completeness. Missing required facts intentionally withhold the v2 score.
API documentation is available at `/docs`. Runtime API requests read cached macro
observations; refresh is an explicit script, not a network request on every page load.
Use a current `--as-of` date when refreshing after the date above.

## Limits and next work

- Regimes describe known conditions; they do not predict equity prices or recessions.
  Historical episode inspection is not a labeled out-of-sample accuracy evaluation.
- The v2 score has provisional product weights and mappings, not scientifically
  validated thresholds or CFPB questionnaire equivalence. Legacy `/api/health`
  remains unchanged. Complete inputs do not guarantee truthful user statements.
- Financial facts are per-request and not stored. Persisting confirmed facts and
  assessment history, production authentication and refresh scheduling need backend
  ownership. Demo customer scoping is not production authorization.
- Exact release timestamps are unavailable. FRED vintage query dates establish
  availability by that date; initial-release dates are recorded where obtainable.
  Yahoo history is not a verified point-in-time archive; check licensing before
  production use. Missing and stale observations reduce coverage explicitly.
- Income variation is diagnostic, not a separate score penalty. Full historical
  savings-rate attribution and restricted-reserve eligibility require more data.
- Essential-cost scenarios use the confirmed aggregate essential budget, not
  invented category allocations. Rate stress uses a user-specified extra payment,
  not a fabricated amortization forecast. Delaying pay shifts subsequent recurrences.
- Investment exposure fields are supported by API facts; the current form does not
  collect holdings or near-term investment cash needs. No blanket spending or
  borrowing instruction is triggered merely because equities decline.
- Live paid Gemini/OpenAI narration was not tested. Offline scoped tool execution
  was tested; existing numeric checks do not establish complete semantic grounding.

Methodology and results: [indicators](ECONOMIC_INDICATORS.md),
[classification](ECONOMIC_CLASSIFICATION_METHODOLOGY.md),
[score formulas](FINANCIAL_HEALTH_SCORING_METHODOLOGY.md),
[historical replays](ECONOMIC_BACKTEST_REPORT.md),
[score validation](FINANCIAL_SCORE_VALIDATION.md).
