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
