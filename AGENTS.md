# FinPilot project instructions

## Scope and sources of truth

- Product name: **FinPilot**. FinSight and ForeCastle are historical names.
- This workspace currently owns Member 3's intelligence layer. Member 2 owns FastAPI, Supabase, authentication and ingestion; Member 1 owns the frontend.
- Read `GLOSSARY.md`, `docs/api-contracts.md` and the relevant implementation before changing financial behavior.
- Treat `docs/model-card.md` and the reports under `artifacts/reports/` as the source for measured performance. Never invent metrics or describe synthetic results as real-world validation.
- Inspect installed code or primary documentation before assuming an SDK function exists. Distinguish implemented, tested, proposed and unavailable behavior.

## Engineering workflow

- Make small changes with explicit observable behavior. Reuse the current functions before adding layers or dependencies.
- For calculation bugs, first reproduce the failure and use a regression test with an independently worked expected result. Test public behavior instead of copying the implementation into assertions.
- Run `powershell -ExecutionPolicy Bypass -File scripts/check.ps1` for Python behavior changes. For documentation-only changes, check links and `git diff --check` as appropriate.
- Run training and recursive backtesting when changing targets, features, splits or model selection; update the model card only from actual reports.
- State what was tested, what was not tested, and relevant limitations. A mock API test does not establish live API compatibility.
- Use the installed project skills when their descriptions fit; they are references, not an instruction to launch every workflow for each task. Preserve the user's established scope and preferences.

## Financial invariants

- Training features must use only information available before the target date. Holdout customers must stay out of fitting and model selection.
- Variable spending excludes scheduled bills and internal transfers. Do not count credit-card consumption and card payments as two expenses.
- Checking projections and savings are separate. Savings transfers preserve combined liquid wealth and can worsen checking liquidity.
- Percentage scenario values are fractions 0..1; macroeconomic indicator values are percentage points. Reject nonfinite numbers.
- Health scores and Guardian rules are transparent heuristics, not credit scores or validated risk probabilities.
- Quantile spending ranges and accumulated balance stress envelopes are not calibrated guarantees.
- Never fabricate current economic observations, bank balances, tool results or model accuracy.
- Keep model predictions separate from scheduled financial arithmetic and LLM explanations. The LLM cannot move money or choose another customer's records.

## Data and secrets

- Use synthetic data only in examples and committed artifacts. Never print or commit API keys or service-role credentials.
- Intelligence functions accept normalized inputs and return results. Database reads, authorization and persistence belong to Member 2's backend.
- Local training artifacts are under `artifacts/models/`; reports under `artifacts/reports/`. Do not edit generated model text manually.

## Installed engineering skills

Project-local skills under `.agents/skills/`: `tdd`, `diagnosing-bugs`, `codebase-design`, `domain-modeling`, `code-review`, `writing-for-agents`.

Source and installation details: `docs/engineering-workflow.md`. The skills improve development discipline; they do not modify FinPilot's inference model.
