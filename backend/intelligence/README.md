# Intelligence modules (Member 3)

Drop a module here and the gateway uses it instead of the built-in baseline. Missing module or
function means baseline runs. If your function raises or returns the wrong type, the baseline runs
and the response carries `meta.warning`. `INTELLIGENCE_MODE=baseline` ignores this package.

Rule: return the Pydantic model from `app/schemas`; do not invent balances. Inputs are plain data
(`app/calc/models.py`: `FinancialProfile`), so you can unit-test with `tests/factories.py`.

| Module | Function | Returns |
|---|---|---|
| `health_score.py` | `compute_health_score(profile)` | `HealthResult` |
| `forecasting.py` | `forecast(profile, days)` | `ForecastResult` |
| `guardian.py` | `evaluate(profile, forecast)` | `list[Alert]` |
| `simulator.py` | `simulate(profile, scenario)` | `SimulationResult` |
| `copilot.py` | `chat(messages, tools)` | `ChatResult` |
| `economic_pressure.py` | `compute(indicators, profile)` | `EconomyResult` (next priority) |

## Integrated Member 3 package

The current services actually look up `forecast.forecast` and `simulate.simulate`. Thin `forecast.py` and `simulate.py` adapters provide these names; original `forecasting.py` and `simulator.py` engines remain available to CLI callers. `backend_adapter.py` translates FinancialProfile and preserves the backend's dated Decimal cash schedules.

Health and Guardian now expose typed functions alongside original functions. Copilot supports the backend messages/ToolRegistry signature and the original dictionary signature. Economic models/classifiers remain standalone; no EconomyResult endpoint is claimed.

See repository-root `docs/TEAM_INTEGRATION.md` for setup and mappings. `docs/api-contracts.md` is the backend wire contract; `docs/intelligence-contracts.md` preserves the original Member 3 contract.
