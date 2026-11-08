# Backend Handoff for Member 1 (Frontend) and Member 3 (AI/ML)

Status: backend MVP is built and **live**: https://finsight-api-7odx.onrender.com (browse `/docs` for a clickable API page; open `/healthz` a few minutes before a demo because the free server sleeps when idle). Data shapes: `/openapi.json`. Real example responses: `docs/examples/`; endpoint table: `docs/api-contracts.md`. The live demo date is pinned to 2026-11-07, so the story is always: checking $2,400 → Guardian warns of a $367 low on Nov 17 → a $200 cut lifts it to $567.

## Member 1 (Frontend)

- Run the backend locally: `cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && .venv/bin/uvicorn app.main:app --reload` → http://localhost:8000/docs. It works with **no database** (built-in demo customer).
- Endpoints: `GET /api/dashboard, /accounts, /transactions, /health, /forecast?days=7|30|90, /guardian` · `POST /api/simulate, /api/chat`. All take optional `?user_id=` (defaults to the demo customer).
- Every computed response has `meta.source` (`baseline` or `model`) and `meta.is_prototype_estimate`; show a "prototype estimate based on simulated data" label.
- Each Guardian alert has `suggested_scenario`: send it unchanged as the body `{"scenario": ...}` to `POST /api/simulate` for the Detect → Simulate link.
- Chat is stateless: send the full `messages` list every time (max 20 messages, 2,000 characters each).

## Member 3 (AI/ML)

The backend ships simple deterministic versions of everything so the demo works now. **Your modules replace them automatically**: create a file in `backend/intelligence/` with the function below. If your function is missing, raises, or returns the wrong type, the backend falls back to its version and sets `meta.warning`.

| File | Function | Returns |
|---|---|---|
| `health_score.py` | `compute_health_score(profile)` | `HealthResult` |
| `forecasting.py` | `forecast(profile, days)` | `ForecastResult` |
| `guardian.py` | `evaluate(profile, forecast)` | `list[Alert]` |
| `simulator.py` | `simulate(profile, scenario)` | `SimulationResult` |
| `copilot.py` | `chat(messages, tools)` | `ChatResult` |

- `profile` is a `FinancialProfile` dataclass (`app/calc/models.py`): user, accounts, last 180 days of transactions, bills, income sources, `as_of`. Plain data, so you can unit test with a hand-built profile and no database.
- Return types are Pydantic models in `backend/app/schemas/`. Do not change them without telling the backend owner and Member 1.
- `tools` (for the Copilot) is a read-only registry: `tools.specs()` gives OpenAI function-calling definitions; `tools.call(name, args)` runs one. The LLM must explain tool results and never invent balances.
- Force the backend's versions (for comparison/demos) with `INTELLIGENCE_MODE=baseline`.
- Suggested delivery order: health score → forecast → Guardian → simulator → Copilot.
- Do you already have code with different function names? Tell the backend owner **now**, and we adapt the contract before more is built.
