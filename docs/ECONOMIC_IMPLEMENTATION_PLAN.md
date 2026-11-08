# Existing implementation and staged plan

Inspected before implementation, November 7, 2026.

| Existing code | Actual behavior | Reuse / change |
|---|---|---|
| `scripts/fetch_economy.py` | Four public FRED CSV series, current-revised cache | Keep research cache; add official-API adapter with vintage metadata |
| `intelligence/economic_outlook.py` | Transient Ridge/logistic research; baseline gates fail | Preserve; do not retrain or expose directional predictions |
| `intelligence/conditions.py` | Fixed inflation/labor/rate/market thresholds | Preserve legacy interface; introduce documented multidimensional classification |
| `intelligence/health_score.py` | Version-1 heuristic, original proposal weights | Preserve definition; add explicitly versioned assessment |
| `intelligence/forecasting.py`, `app/calc/projection.py` | ML spending plus cash arithmetic | Reuse Decimal scheduler for known-obligation stress tests; forecasts not authoritative |
| `app/calc/models.py`, `metrics.py` | Owned accounts, signed movements, bills, income; optional liability links | Reuse; record unsupported completeness rather than assume absent means zero |
| `app/tools/registry.py` | Profile-scoped calculation tools | Extend without customer-ID selection |
| `frontend/src/ConnectedDashboard.tsx` | Dashboard/forecast live; economic page is a design preview | Add actual economic, assessment and stress UI |
| `reports/reliability/` | Synthetic cash errors remain high; cold-start and accounting fixes | Preserve artifacts; do not claim real-world validation |

Stages: (1) research/methodology; (2) provider ingestion with versioned caches and
availability checks; (3) rule-based macro dimensions and versioned personal score;
(4) deterministic resilience/scenarios, API/tools/UI; (5) invariants, sensitivity,
historical release-aware replay and documentation. No existing model retraining.
Missing publication vintages must withhold historical classification rather than
replay current-revised observations as if they were known in the past. New score
weights are explicit product assumptions, not validated CFPB questionnaire weights.
