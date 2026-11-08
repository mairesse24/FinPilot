# FinPilot shared terminology

| Term | Meaning in this repository |
| --- | --- |
| FinPilot | Current product name; formerly FinSight / ForeCastle. |
| Intelligence layer | Member 3's importable functions under `backend/intelligence/`. |
| Customer snapshot | Normalized balances, monthly assumptions, schedules and an `as_of` date. |
| Variable spending | Daily consumption in groceries, transport, dining, shopping and other_spending; excludes scheduled housing/utilities and transfers. |
| Spending forecast | ML estimate of variable spending for future days. |
| Cash projection | Arithmetic combining forecast spending, scheduled income, scheduled bills and starting checking cash. |
| Lower / median / upper model | LightGBM quantile regressors at 10%, 50% and 90% for daily variable spending. |
| Forecast horizon | Number of future days, up to 90; not a separate trained model. |
| Stress envelope | Accumulated low/high balance paths from spending quantiles; not a calibrated balance prediction interval. |
| Health score | Explainable, weighted internal wellness heuristic; not a credit score. |
| Guardian | Deterministic risk rules with evidence and suggested hypothetical scenarios. |
| Digital Twin | In-memory before/after scenario calculation; does not change bank accounts. |
| Economic pressure | Heuristic calculated from a supplied dated economic snapshot; no live feed in this package. |
| Copilot | Optional LLM explanation and tool-calling layer over verified calculations; offline mode produces a fixed summary. |
| Held-out customer | Customer whose records do not enter model fitting or selection. |
| Chronological test | Later dates reserved for evaluation after training and validation. |
| Recursive forecast | Multi-day forecast that feeds earlier predictions into subsequent days' features. |
| MAE | Average absolute prediction error, expressed here in USD per customer-day. |
| Internal transfer | Money moved between accounts; not new income or consumption. |

The precise input/output contract lives in `docs/api-contracts.md`; model assumptions and evaluation limits live in `docs/model-card.md`.
