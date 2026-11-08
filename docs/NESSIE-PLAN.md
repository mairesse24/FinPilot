# Nessie enablement plan

Date: 2026-11-08. Status: **plan only; nothing in the Nessie sandbox has been changed.**
Code that already exists (branches `test`, `mongodb`, `gokul`): importer `backend/app/data/nessie.py`, seeder `scripts/seed_nessie.py`, lister `scripts/nessie_customers.py`, tests `backend/tests/test_nessie.py`, docs `docs/FRONTEND_INTEGRATION.md`.

## 1. What I verified (read-only, 2026-11-08)

| Item | Result |
|---|---|
| `NESSIE_API_KEY` | Valid. Customer lookup returns 200. |
| `NESSIE_CUSTOMER_ID` | Valid: "Alex FinPilot Demo". |
| Sandbox contents | 3 accounts: checking **$6,500**, savings $600, credit card $420. One approved auto loan ($5,000 original, $150/month). 40 completed purchases (2026-07-11 to 2026-11-05). 8 completed deposits (2026-07-31 to 2026-11-06). 0 withdrawals. |
| `AS_OF_DATE` | `2026-11-07` (valid; fixed since the last check). |
| Gemini key | Valid. Model `gemini-3.8-flash` exists but a tiny test call returned **503 "high demand"**. `gemini-3.1-flash-lite` answered in 0.5 s. (One sample each; Gemini load varies.) |
| `FRED_API_KEY` | Present (32 hex characters). Economic refresh is possible. |
| `NESSIE_SCHEDULES_FILE` | **Broken for us:** `C:\Users\sivar\Documents\FinPilot\data\synthetic\nessie-schedules-local.json` is a Windows path on a teammate's computer. It does not exist on this Mac or on Render, and the file is not in the repo. |

## 2. Problems this plan solves

1. **Schedules file missing** (income and bills): without it the forecast assumes no future income and no bills.
2. **The demo story does not fire with this customer.** Checking is $6,500; bills before payday are about $1,805 and variable spending about $20 a day, so the balance never drops below the $500 buffer. Guardian shows no low-balance alert.
3. **No fallback by design.** With `DATA_SOURCE=nessie`, a Nessie error at startup stops the whole backend.
4. **Chat is slow** because `gemini-3.8-flash` returns 503 or 504 under load.

## 3. Decisions needed

| # | Decision | Options | Recommendation |
|---|---|---|---|
| D1 | Which customer tells the story? | **A.** Create a *new* sandbox customer with the checking balance lowered to $2,400 (one write run of `scripts.seed_nessie --apply`). The seeder also writes the schedules file. **B.** Keep the existing $6,500 customer and tell a different story: use the Digital Twin with an emergency expense or income cut. | **A.** It is the same story as the pitch ($2,400, then Guardian warns, then a $150 cut over 10 days). |
| D2 | Copilot model | Keep `gemini-3.8-flash`, or switch `GEMINI_MODEL` to `gemini-3.1-flash-lite` | Switch. It answered in 0.5 s while the other returned 503. One setting, no code. |
| D3 | Where does Nessie run? | Replace the MongoDB service, or run a **second** Render service | Second service (`finpilot-nessie`). The MongoDB service stays as the safe fallback. |
| D4 | Which frontend UI? | Current Netlify site (branch `mongodb`) or the redesigned UI on branch `test` | Ask the team. If `test`'s UI is the demo UI, build it with the Nessie backend address. |

## 4. Steps

**Step 0 — Your `.env` (you, 1 min)**
- Change `GEMINI_MODEL` to `gemini-3.1-flash-lite` (D2).
- Do not change the Windows path yet; step 3 replaces it with a repo-relative path.

**Step 1 — Schedules file (me, 5 min, no sandbox change)**
- If D1 = B: build the file for the existing customer from the sandbox (customer id, the approved loan's id with remaining balance 5000, income $2,100 biweekly next on 2026-11-18, bills: rent $1,500 on 11-11, utilities $120 on 11-13, card minimum $35 on 11-15, auto loan $150 on 11-16). Same values the seeder writes.
- Save as `data/synthetic/nessie-schedules-demo.json` (no secrets), committed. Set `NESSIE_SCHEDULES_FILE=data/synthetic/nessie-schedules-demo.json` (relative; works when the backend starts from the repo root, locally and on Render).

**Step 2 — New customer for the story (me, 10 min; D1 = A only; needs your explicit "yes")**
- Change the seeder's checking balance from 6500 to 2400 and show the dry run.
- Run `scripts.seed_nessie --apply`: creates 1 fictional customer, 3 accounts, an auto loan, 1 merchant, 40 purchases and 8 deposits in your sandbox. Nothing existing is changed or deleted.
- The seeder writes `data/synthetic/nessie-schedules-local.json`; I copy it to `nessie-schedules-demo.json` and update `NESSIE_CUSTOMER_ID` to the new id.

**Step 3 — Local run and proof (me, 10 min)**
- Check out `test` in its own folder, create a local `.env` (gitignored) with the settings above.
- Run `python -m scripts.nessie_customers` (read-only), then the backend with `DATA_SOURCE=nessie`.
- Check: `/api/context` says "Nessie sandbox"; Guardian shows a low-balance alert (about $395 projected low); the suggested cut fixes it; `/api/chat` answers in under 3 s.
- Run `pytest backend/tests/test_nessie.py` (expect all pass).

**Step 4 — Second Render service (you, 10 min, with my exact values)**
- New Web Service from `https://github.com/mairesse24/FinPilot`, branch `test`, Root Directory empty, build `pip install -r backend/requirements.txt`, start `uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port $PORT`, Free.
- Environment: `PYTHON_VERSION=3.12.7`, `DATA_SOURCE=nessie`, `NESSIE_API_KEY`, `NESSIE_CUSTOMER_ID`, `NESSIE_SCHEDULES_FILE=data/synthetic/nessie-schedules-demo.json`, `AS_OF_DATE=2026-11-07`, `CORS_ORIGINS=*`, `COPILOT_PROVIDER=gemini`, `GEMINI_API_KEY`, `GEMINI_MODEL=gemini-3.1-flash-lite`. Optional: `FRED_API_KEY`.
- Needs the schedules file pushed to branch `test` (or `mongodb`, then choose that branch).

**Step 5 — Frontend (me + you, 10 min)**
- Rebuild the frontend with `VITE_API_BASE=<new Render address>` and drop `dist` on a second Netlify site, or replace the current one once Nessie is proven.

**Step 6 — Final check (me, 5 min)**
- Run every endpoint against the new service, including chat timing.

## 5. Risks and rollback

| Risk | Mitigation |
|---|---|
| Nessie down at startup stops that backend | MongoDB service stays untouched as the fallback. |
| Gemini 503 under load | Model switch (D2); template fallback exists; `COPILOT_PROVIDER=offline` for an instant reply. |
| Secrets | `.env` is gitignored. Never put keys in the frontend or the repo. The importer removes the key from error messages. |
| Thin history (40 purchases) | The forecast uses the rolling-average fallback; disclose it. |
| Date drift | Keep `AS_OF_DATE` pinned to the seed date. |
| Rollback | Delete the second Render service and the second Netlify site. The sandbox customer can stay; it is fictional. |

## 6. Done means

- `/api/context` reports the Nessie sandbox.
- Guardian shows the low-balance alert with a suggested cut that clears the $500 buffer.
- The Digital Twin shows the same story ($2,400, a low near $395, recovery after the cut).
- Chat answers in under 3 s.
- The Nessie tests pass.
- Docs updated; `FUTURE-IMPROVEMENTS.md` item 8 closed.
