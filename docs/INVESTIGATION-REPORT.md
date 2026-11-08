# Investigation report — deployed app and merged branch

Date: 2026-11-08. Branch: `mongodb` (synced with `origin/test` at `a80b246`, "Merge nessie-demo into test", N0tgokul).
Scope: the deployed frontend (Netlify), the live backend (Render, MongoDB), and the merged UI (what will be demoed next).
Related: [FUTURE-IMPROVEMENTS.md](FUTURE-IMPROVEMENTS.md) (model and data items), [NESSIE-PLAN.md](NESSIE-PLAN.md).

## How this was checked

| Method | What it covered |
|---|---|
| Headless Chrome 157 (Playwright, throwaway scripts) | Every page, desktop 1366×900 and phone 390×844: console errors, failed requests, timing, screenshots |
| Lighthouse 12 | Performance, accessibility, best practices, SEO (mobile and desktop) on the deployed site |
| curl | Status codes, CORS headers, file hashes, route lists |
| Local run of the merged backend and merged UI | Proof that problems on the live site come from an old deployment |

Not checked: real Gemini conversations in a browser (the Chrome extension was not connected), the Nessie service on Render (not created yet), accuracy of forecasts on real data.

## Sync status

`origin/test` tip is `a80b246`. It added `5e3645f` (automatic FinPilot Wrapped story) and `6157525` (the Nessie seeder commit from `nessie-demo`). The `mongodb` branch contains all of it. The merge had no conflicts. `test` was only read. `mongodb` is 15 commits ahead of GitHub; none of it is pushed.
Backend tests on the merged branch: 198 pass, 15 fail. All 15 failures are the same Mac-only missing library (`libomp`) and fail identically on a pristine `test`.

## Ranked fix list

Priority: **P0** = breaks or blocks the demo. **P1** = hurts the demo noticeably. **P2** = polish. **P3** = housekeeping.

### P0 — fix before presenting

**1. The live backend is older than the merged code. Health Score shows "Not Found".**
- Evidence: the merged UI calls `/api/financial-inputs`. The live backend returns **404**. The merged backend returns 200. With the merged backend running locally, all pages load and the Health Score page shows an 80.06 score ring. Console shows two 404 errors on the live backend.
- Fix: push `mongodb`, then Manual Deploy the Render service that tracks it. Do this **before** step 2.
- Effort: 10 minutes. Owner: you.

**2. The deployed frontend is the first drop (old UI).**
- Evidence: still serves `index-4GkFAzox.js` with `<title><!-- figma:title --></title>` and an invalid language. The merged build has the title "FinPilot", language `en`, and a favicon.
- Fix: rebuild with `VITE_API_BASE=<backend address>` and drop `dist` on Netlify (see `frontend-deploy.md`). Deploy only after the backend (item 1).
- Effort: 5 minutes. Owner: you (I build the folder).

**3. The demo story is not visible in the UI.**
- Evidence: the UI never calls `/api/simulate`. Guardian says "Compare the suggested spending scenario" but offers no button. The "what-if" box offers 10 stress scenarios (cost increase, income reduction, missed paycheck, emergency expense, savings transfer and others) but no "cut discretionary spending", which is the fix Guardian recommends. The Guardian page repeats the Overview.
- Fix: a "Test this fix" button on the Guardian alert that calls `/api/simulate` with the alert's `suggested_scenario` and shows before and after ($358.50 low becomes $508.50 after a $150 cut over 10 days).
- Effort: 1–2 hours. Owner: frontend (Member 1) or me.

### P1 — hurts the demo

**4. Pages take 5–7 seconds on the live backend (1.6 seconds locally).**
- Evidence: `/api/dashboard` and `/api/forecast` each take about 5.4 s when called together (about 2.7 s alone). Overview, Guardian and Wrapped wait about 5–6 s. Lighthouse performance: mobile 41, desktop 52; largest content appears at 6–8 s.
- Cause (likely): free-tier CPU, one worker, both calls recompute health, Guardian and forecast.
- Fix: fetch dashboard and forecast once and share between pages; cache results on the backend for 30–60 s; keep the pinger running; open each page once before presenting.
- Effort: 1 hour. Owner: backend and frontend.

**5. Copilot chat is slow or falls back.**
- Evidence: `gemini-3.8-flash` returned 503 "high demand" on a test call; `gemini-3.1-flash-lite` answered in 0.5 s. Live chat took 34–41 s before the template answered.
- Fix: set `GEMINI_MODEL=gemini-3.1-flash-lite` in Render. Lower the Gemini timeout from 30 s to about 8 s. Decide which Copilot ships (branch `feature/ai-copilot` conflicts with Member 3's). Quick option: `COPILOT_PROVIDER=offline` for instant template replies.
- Effort: 5 minutes (setting) to 1 hour (timeout and merge). Owner: Member 3 and you.

**6. Several navigation items show the same content.**
- Evidence: Guardian, My Finances and Wrapped (old build) show the Overview content. Health Score, Digital Twin, Economic Lab and AI Co-Pilot show one shared page (about 1,000 characters each, only the heading changes). The merged UI adds a real Wrapped story page.
- Fix: give each page its own content, or merge duplicates in the navigation.
- Effort: 2+ hours. Owner: Member 1.

**7. Two different health scores.**
- Evidence: Overview shows the legacy score (77.5 on the live site); the Health Score page shows a different estimate (80.06 in the local run).
- Fix: show one headline score, or label them ("legacy v1" and "v2 estimate") and explain.
- Effort: 30 minutes. Owner: Member 1 and Member 3.

**8. Nessie service is not running anywhere yet.**
- State: sandbox customer `af827dd6-f3f3-48c4-8540-b4d1217abfb6` ($2,400 checking) and the schedules file exist; the story works locally on Nessie data (low $399.01, $547.17 after a $150 cut). A Nessie error at startup stops that service (by design).
- Fix: create the second Render service per `NESSIE-PLAN.md` step 4; keep the MongoDB service as the fallback.
- Effort: 10 minutes. Owner: you.

### P2 — polish

9. **Economic Lab shows "Unavailable" for every indicator** ("Insufficient Data"). Needs a FRED data refresh (key present) and the snapshot available on Render.
10. **Floating Copilot button overlaps content** at the right edge (it partly covers amounts such as "Utilities $120.0…" on Overview). Adjust position or page padding.
11. **SEO and accessibility:** no meta description (SEO 90). The invalid page language is fixed in the merged build; the deployed site still has it. Accessibility 95, best practices 100.
12. **What-if scenario names are raw** ("essential cost increase", "variable rate payment"); add plain-language labels and short explanations.
13. **Forecast method wording:** Alex's forecast uses the rolling-average fallback; do not claim LightGBM drives it (see `FUTURE-IMPROVEMENTS.md` items 1–5).

### P3 — housekeeping

14. **Git:** `mongodb` is 15 commits ahead of GitHub. Decide one demo branch, push it, and merge into `main` through a pull request. Reconcile the two Copilots first.
15. **Tests on Mac:** 15 tests fail because `libomp` is missing (`brew install libomp`). They are expected to pass on Linux, but that is unverified.
16. **npm cache permissions:** `~/.npm` has root-owned files (npm suggests `sudo chown -R 501:20 ~/.npm`). Not required; tools can use a temporary cache.
17. **Secrets:** `.env` holds many keys (Nessie, Gemini, FRED, MongoDB, database). Never commit it. Rotate any key that was ever pasted into chat.

## What works well (verified)

- No JavaScript errors on any page, on desktop or phone; no sideways scrolling on a phone.
- All API calls return 200 with correct CORS headers (`*`).
- Data on screen matches the API: net worth $2,580, checking $2,400, low $358.50, bills and categories.
- The Guardian suggestion now clears the buffer ($150 over 10 days: $358.50 becomes $508.50).
- The merged UI is a clear step up: cleaner layout, Wrapped story page, "Improve estimate accuracy" flow, automatic health estimate.
- Wrapped story page works and opens with the net worth and "Start the story".

## Suggested order (about 2 hours)

1. Push `mongodb`; redeploy the backend (item 1) — 10 min.
2. Set `GEMINI_MODEL` in Render (item 5, setting only) — 5 min.
3. Rebuild and drop the frontend (item 2) — 5 min.
4. Build the "Test this fix" Guardian button (item 3) — 1–2 h.
5. Share data between pages and add a short backend cache (item 4) — 1 h.
6. Create the Nessie service (item 8) — 10 min.
7. Re-run the browser check against the deployed site to confirm.
