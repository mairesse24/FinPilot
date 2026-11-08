# Future improvements and known issues

Read this file first when asked "what should we improve / fix next?". Update it when an item is done or a new one is found.
Last updated: 2026-11-08, after the MongoDB switch and the `gokul` merge.

> Ranked, current fix list with evidence: [INVESTIGATION-REPORT.md](INVESTIGATION-REPORT.md) (2026-11-08).

Status key: **OPEN** = not done. **DEMO-RISK** = could hurt a live demo. **LATER** = safe to defer.

## 1. Uncertainty-band calibration does not match the committed model files — OPEN, LATER

- **What:** `backend/intelligence/interval_calibration.json` stores the SHA-256 fingerprints of the model files it was fitted on. `backend/intelligence/intervals.py` (`policy_for`) switches calibration off if any of `artifacts/models/lower.txt`, `median.txt`, `upper.txt` has a different fingerprint. The model files committed in `8ff86df` ("Add trained LightGBM quantile models") have different fingerprints, so calibration is currently **off**.
- **Effect:** the forecast shows the plain 10th–90th percentile range from the quantile models. Nothing breaks. But `docs/model-card.md` text about "calibrated residual bands" does **not** apply to the committed files. Observed coverage on synthetic data is 95.7% against a nominal 80%.
- **Fix:** Member 3 re-fits the calibration on the committed models (the training and calibration scripts under `scripts/` and `reports/ml_evaluation/`), commits the new `interval_calibration.json`, and re-checks coverage. Then update the model card.
- **Check it worked:** the three fingerprints in `interval_calibration.json` equal `sha256sum artifacts/models/{lower,median,upper}.txt`.
- **Note:** `artifacts/models/` and `vendor/` are listed in `.gitignore`. The model files were force-added. Future retrains need `git add -f artifacts/models/*`.

## 2. The ML forecast does not run for the demo customer (Alex) — OPEN, DEMO-RISK (wording)

- **What:** `forecasting.py` only uses LightGBM when the history has at least 90 days and a zero-spending-day fraction of at least 0.683 (training minimum 0.833 minus a 0.15 margin). Alex spends every day, so the fraction is 0.000. Alex gets the labeled rolling-average fallback.
- **Effect:** do not say LightGBM drives the live forecast for Alex. Say it was trained and evaluated on PNC synthetic data and is used when a customer's history fits the training data.
- **Fix options:** (a) make a demo customer whose spending pattern resembles the PNC data, then re-tune the demo story; (b) add a second demo customer from PNC-style data.

## 3. Accuracy claims need fair wording — OPEN, DEMO-RISK (wording)

- LightGBM MAE $2.62 against a 28-day average of $169 looks like a 60× gain. The fair baseline is "same day last month" at $3.63, so the real gain is about $1. The data is synthetic and highly predictable.
- Say: "comparable to a same-day-last-month baseline on synthetic data; not evidence of real-customer accuracy."

## 4. Forecast optimism for the ML path — OPEN, LATER

- The ML path feeds daily medians forward. On spiky spending the median is about $0 on most days, so the summed total understates spending (the code comments admit this). The cash projection can be too optimistic, so Guardian may under-warn.
- Fix: use a mean-based total or label the ML total as a planning figure only. The rolling-average path (Alex) is not affected.

## 5. Payday feature is hardcoded — OPEN, LATER

- `backend/intelligence/features.py` computes `payday_distance` from the 1st, 15th and 28th of the month (the PNC data is semi-monthly). Customers paid biweekly (Alex) or on other days get a wrong feature value.
- Fix: derive paydays from the customer's income schedule, then retrain.

## 6. "Stress envelope" bands are very wide — OPEN, LATER

- `project_cash` in `forecasting.py` adds every day's upper (or lower) bound together. This is a worst-case stress range, not a probability range. Make sure the frontend labels it "stress range", never "expected range".

## 7. Health score definitions differ between versions — OPEN, LATER

- Member 3's emergency savings divides by **all** outflows; the PDF and the backend baseline use **essential** expenses only (1.05 against 1.38 months for Alex).
- Spending discipline needs a budget. A demo budget can be supplied with the environment variable `DEFAULT_MONTHLY_BUDGET` (for example 1100). A real budget field on the user record is the proper fix (database, schema, seed, API).

## 8. Nessie sandbox API not integrated — OPEN, LATER

- The importer (`backend/app/data/nessie.py`) and the seeder exist and pass tests with fake data. It has never run against the real service.
- Blocker: no `NESSIE_API_KEY` or sandbox customer in any `.env`. The service `api.nessieisreal.com` is reachable. A bad key does **not** give an auth error: lists return `200 []` and a single customer returns 404, which the importer reports as one generic "check sandbox host, key and customer ID" message.
- Limits: it loads one customer once at startup, ignores savings, card and ATM activity, and needs a schedule file for income and bills; unlabeled purchases become category `other`.
- Keep `DATA_SOURCE=demo` in Render until this is done.

## 9. Deployment and hosting — OPEN

- Frontend and backend are to be hosted separately (backend on Render, frontend on Vercel or Netlify with an `/api` rewrite to the Render address). Not done yet; the frontend runs only on a laptop (Vite proxy to `127.0.0.1:8000`).
- Render services created from a public repo link do not redeploy on push. Use **Manual Deploy → Deploy latest commit**.
- Free Render instances sleep after about 15 minutes idle; open `/healthz` before a demo. The free tier has 512 MB of memory; the ML libraries are heavy.
- After the demo: decide whether to remove Supabase/Postgres code (`backend/app/db/postgres.py`, `schema.sql`, `psycopg`) so MongoDB Atlas is the only database. Kept as a fallback for now.

## 10. Smaller cleanups

- `Gemini` copilot: timeouts of 30 s with one attempt can make chat take over 40 s when Google returns 503 or 504. Lower the timeout to about 8 s. Branch `feature/ai-copilot` has a newer Gemini copilot that is not merged yet.
- Gateway fallback label: the forecast reports `"source": "baseline"` even when Member 3's adapter shapes the numbers. Cosmetic.
- Tests that need LightGBM fail on a Mac without `libomp` (`brew install libomp` fixes it). They pass on Linux.

## 11. Two Copilot implementations to reconcile — OPEN, DEMO-RISK

- Branch `feature/ai-copilot` (commit `9153787`, mairesse24) is a second, independent Gemini Copilot built from the `backend-mvp` lineage. Member 3's Copilot on `gokul` writes the same file `backend/intelligence/copilot.py`. A test merge conflicts in `config.py`, `routes/chat.py`, `services/gateway.py`, `tools/registry.py`, `intelligence/copilot.py` and `requirements.txt`.
- Why it matters: live chat takes about 34 s because Gemini returns `504 DEADLINE_EXCEEDED` and the app waits before falling back. The feature branch reports 0.9–1.7 s after its latency work (its own measurements, `docs/copilot-performance.md`; not verified).
- Decide with the team which Copilot ships, then merge on a separate test branch and re-run the tests. Quick demo mitigation without code: set `COPILOT_PROVIDER=offline` in Render for instant template replies.

## 12. Frontend hosting — OPEN

- Deployed manually with Netlify Drop (see `docs/frontend-deploy.md`); redeploy by rebuilding and dropping `dist` again. Move to a Git-connected deploy (auto-build on push) once the repo owner can authorize it.

## 13. FinPilot Wrapped — suggestions only, no changes planned — OPEN, LATER

Decision (2026-11-08): the Wrapped story page (`frontend/src/FinPilotWrapped.tsx`, commit `5e3645f`) looks good and is **not** being changed. These are observations to revisit after the demo. Only the opening slide ("Your FinPilot snapshot", net worth, "Start the story", "Manual mode") was viewed; the other slides, the manual mode and phone widths were not walked.

- **Load time against the live backend:** the page fetches its own `context`, `economy`, `dashboard` and `forecast`; it was ready after about 7 s on the live backend (about 2 s locally). A shared data cache (see `INVESTIGATION-REPORT-CONSOLIDATED.md` C-05) would remove most of the wait.
- **Loading state:** "Building your financial story…" is a plain text line; a skeleton or progress hint would feel faster.
- **Route alias:** `#/wrapped` renders the Overview content (breadcrumb "Workspace / Overview"); the working route is `#/finpilot-wrapped`. An alias would avoid a broken-looking link.
- **Untested:** the remaining slides, manual mode, keyboard use, phone layout, and behavior when the API is down.
