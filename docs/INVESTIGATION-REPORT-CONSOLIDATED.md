# FinPilot — Consolidated Investigative Report

Date: 2026-11-08 · Branch: `mongodb` (synced with `origin/test` at `a80b246`)
Scope: investigation, evaluation and report only. No website changes and no fixes were made.

## 1. How this report was produced

| Step | What was done |
|---|---|
| Inputs | Three independent reports: **R1** [INVESTIGATION-REPORT.md](INVESTIGATION-REPORT.md) (backend, deployment, Lighthouse, models), **R2** [INVESTIGATION-REPORT-2.md](INVESTIGATION-REPORT-2.md) (live click-through, FP-01..FP-11), **R3** [INVESTIGATION-REPORT-3.md](INVESTIGATION-REPORT-3.md) (Overview audit, P0.1..P2.0). |
| Judge | One independent read-only judge agent compared all three against the live sites, the source code and the live API. Its full evaluation is saved as [INVESTIGATION-JUDGE-EVALUATION.md](INVESTIGATION-JUDGE-EVALUATION.md) (44 distinct issues). |
| Consolidation | Done by the main assistant. I read the three reports and the judge's evaluation, then **re-verified the judge's highest-impact claims myself** (section 7), corrected the judge in two places (section 8), and resolved contradictions on evidence, not majority. |

Line numbers in this report come from the judge's evaluation unless marked "re-checked".

### Scope notes from the project owner (2026-11-08)

- **Reference build:** the latest version is the app run locally after syncing with `origin/test` (`a80b246`) at `http://127.0.0.1:5180/#/overview`. Its frontend code is identical to the "merged UI" used in this report (checked by comparing the two folders). Findings marked old-build apply only to the deployed Netlify sites.
- **Wrapped is out of scope for fixes.** No change is planned to the FinPilot Wrapped story page. Related observations are recorded as suggestions in [FUTURE-IMPROVEMENTS.md](FUTURE-IMPROVEMENTS.md) item 13. In this report, Wrapped is mentioned only as a difference between builds (C-04) and as a data-loading example (C-05).

### Which build each report looked at (this explains most disagreements)

| Build | Where | What it is |
|---|---|---|
| **Old UI** | Netlify site A `boisterous-cassata-005b39` and site B `mellow-brigadeiros-9dbbfa` | Same JavaScript on both (`index-4GkFAzox.js`, sha256 `12f84b60adfa2699`, re-checked). Site B only has a patched `index.html` (title "FinPilot", lang, favicon) and a Netlify badge script. |
| **Merged UI** | `frontend/src` on branch `mongodb` (built to `frontend/dist`) | The teammate's redesigned UI, including the Wrapped story page. Not deployed anywhere yet. |
| **Live backend** | `finpilot-o0gj.onrender.com` | Older than the merged backend (for example `/api/financial-inputs` returns 404). |

R2 and R3 described the **old UI** (R3 quotes `legacy v1` and `forecast_unvalidated ? forecast`). R1 tested the old UI on site A and the merged UI locally.

## 2. Executive summary

- **What works:** numbers reconcile (net worth $2,580 = $2,400 + $600 − $420), no JavaScript errors, all API calls return 200, no sideways scroll on a phone, and the Guardian suggestion clears the buffer on the live backend ($358.50 becomes $508.50 for a $150 cut over 10 days).
- **Three blockers (P0):** both deployed sites still run the old UI; the live backend is older than the merged UI needs (four pages show "Not Found"); and the UI has no way to test the Guardian's suggested fix, so the demo story cannot be shown on screen.
- **Seven items that hurt the demo (P1):** duplicate pages, 5–6 s loads with bare "Loading…" text, an empty Economic Lab (caused by a git-ignored data file), conflicting health scores (one silently ignores emergency savings), a Health Score breakdown that contradicts its own score, slow or failing chat (Gemini), and engineering text still visible.
- **Order matters:** redeploy the backend first, then the frontend. Deploying the new frontend onto the old backend breaks the Health Score page.

Counts after consolidation: **3 P0, 7 P1, 13 P2, 7 P3** (30 findings), plus **5 already fixed in the merged build**, **5 design suggestions (not defects)** and **12 removed or corrected claims**.

Severity key: **P0** breaks or blocks the demo · **P1** hurts it noticeably · **P2** polish · **P3** housekeeping.
Verification key: **Verified** (evidence gathered), **Partial**, **Unverified** (could not be checked).

## 3. Ranked findings

### P0 — fix before presenting

#### C-01 · Both deployed Netlify sites run the old first-drop UI
- **Sources:** R1 #2 (R2 and R3 saw it without knowing). Judge J-01. **Verified.**
- **Evidence:** JavaScript is byte-identical on site A and site B (re-checked). Site B's `index.html` has a valid title and language, but still loads `index-4GkFAzox.js`. Site A still has `<!-- figma:title -->`.
- **Root cause:** Netlify Drop of a `dist` built before the redesign; site B only received a patched `index.html`.
- **Fix:** rebuild `frontend/` from `mongodb` with `VITE_API_BASE=https://finpilot-o0gj.onrender.com`, drop it on the demo site **after C-02**, then confirm the served asset hash changed.
- **Correction:** R1's "placeholder title and language" is true for site A only.

#### C-02 · Live backend is older than the merged code; four pages break
- **Sources:** R1 #1. Judge J-02. **Verified** (404 re-checked on live; 200 on merged).
- **Affected:** Health Score, Digital Twin, Economic Lab, AI Co-Pilot (merged UI); the "simulate spending 90% of savings" notification button (`/api/demo/savings-stress` is missing on live).
- **Root cause:** the merged UI calls `/api/financial-inputs`. `EconomicIntelligence.tsx:218-220` (re-checked) wraps `resilience` and `financial-inputs` in one `Promise.all`; one 404 rejects both, so the page shows "Not Found" and every panel stays empty.
- **Fix:** push `mongodb` and Manual Deploy the Render service that tracks it. Optional hardening: use `Promise.allSettled` so the page degrades gracefully.

#### C-03 · No Guardian → simulate ("Test this fix") flow in the UI
- **Sources:** R1 #3 (strongest: endpoint, scenario and numbers), R3 P1.8 (product framing, "$100 cut" example). Judge J-03. **Verified.**
- **Evidence:** the frontend never calls `/api/simulate` (only `economic-simulate` and `demo/savings-stress`). The Guardian alert carries `suggested_scenario` (`spending_cut`, 150, 10 days). A read-only `POST /api/simulate` on the live backend returns baseline low $358.50, scenario low $508.50, end balance $3,747.24 to $3,897.24, score 77.51 to 79.87. The what-if list has ten stress types and no spending cut.
- **Fix:** in the Guardian section of `ConnectedDashboard.tsx` (about lines 307–322), render "Test this fix" when `suggested_scenario` exists, call `POST /api/simulate`, and show before and after. Add a result type to `api.ts`.
- **Severity note:** R3 rated it P1. The judge and I rate it P0 because the demo story depends on it.

### P1 — hurts the demo

#### C-04 · Several routes render the same content
- **Sources:** R1 #6, R2 FP-01. Judge J-04. **Verified**, per build:
  - Old build: Overview = My Finances = Guardian = Wrapped; **Health Score = Digital Twin = Economic Lab = AI Co-Pilot** (text-identical except the heading); Forecasts is a subset.
  - Merged build: Overview = My Finances = Guardian; Forecasts is a subset; the four economic pages are one component with the same six panels in a different order (AI Co-Pilot puts chat first, Health Score puts the score first). Wrapped is now a real story page.
- **Correction:** R2's claim that Health Score is distinct, and that AI Co-Pilot differs only at the bottom, is wrong for the old build. R2 sampled Health Score while it was still loading.
- **Fix (R2's split is the most concrete):** minimum for the demo: give Guardian its own view (alerts plus the simulate button from C-03) and hide or reduce My Finances; mark unfinished routes "Coming soon" instead of duplicating.

#### C-05 · Slow first paint, bare "Loading…" text, no shared data cache
- **Sources:** R1 #4 (measurements, Lighthouse, server cause) and R2 FP-02 (UX symptoms, acceptance test). Judge J-05. **Verified.**
- **Evidence:** live `/api/dashboard` and `/api/forecast` take about 3 s alone and 4.6–6.4 s in parallel; local merged backend about 0.6 s. Old UI on live: Overview first load 5.5 s, Guardian 6.4 s, Wrapped 5.1 s. Lighthouse (site A): performance 41 mobile and 52 desktop; largest content 7.7 s and 6.3 s. No skeleton or spinner exists in the source; loading states are plain text.
- **Root causes (combined):**
  - Frontend: state lives inside each page component, so data refetches on component **remount**, not on every route (Overview, My Finances and Forecasts share one instance and are instant; going to an economic page and back costs another 5–6 s). `/api/context` is fetched up to three times.
  - Backend: the dashboard computes health and Guardian, and the forecast endpoint recomputes; one worker on the free tier.
  - R2's cold-start hypothesis is plausible but not what slowed today's runs (`/healthz` answered in 0.26 s).
- **Fix:** shared data provider keyed by `as_of`, skeleton cards, a "waking the server" message after about 8 s with Retry (R2); backend memoization of 30–60 s (R1); keep the pinger.

#### C-06 · Economic indicators all "Unavailable" (Economic Lab, Digital Twin, AI Co-Pilot)
- **Sources:** R1 #9, R2 FP-03. Judge J-06. **Verified** (re-checked).
- **Root cause:** `backend/intelligence/economic_data.py` reads `data/economic_snapshots/latest.json`. That folder does not exist, and `.gitignore:21` ignores it, so no deploy can include it. `/api/resilience` returns `provider_errors: {"cache": "Run python -m scripts.refresh_intelligence"}`. It is a missing file, not a null feed or missing fixtures.
- **Fix:** run `python -m scripts.refresh_intelligence` once (the FRED key is already set); commit one dated `latest.json` (un-ignore that file) or bake it into the build. UI: replace the wall of tiles with one empty state when data is genuinely missing (R2).
- **Severity:** R1 said P2, R2 High; the judge and I set P1 because three pages lead with the empty tiles.

#### C-07 · Conflicting health scores — and one omits emergency savings
- **Sources:** R1 #7, R2 FP-05, R3 P0.2. Judge J-07 (no report found the root cause). **Verified.**
- **Root cause:** three implementations:
  1. Overview score (legacy v1, `intelligence/health_score.py`; also drives the emergency alert): emergency savings = (checking + savings) ÷ **total** monthly outflow.
  2. Baseline fallback `app/baseline/health.py`: ÷ **essential** spending.
  3. Health Score page (`app/services/economic_intelligence.py`, re-checked): `observed_score` is the weighted mean of **only the supported components**. For this customer that is cash-flow 60.91 and debt 99.22, so (60.91 + 99.22) ÷ 2 = **80.06**; emergency preparedness and payment readiness are withheld. The higher number is less complete, not better.
- **Fix:** pick one headline score. Show v2 on Overview (add `observed_score` to `/api/dashboard` or call `/api/resilience`) with its component count, or label the Overview card as a different measure. Owners: Member 3 (backend) and Member 1 (`ConnectedDashboard.tsx` about 301–305).

#### C-08 · Health Score breakdown contradicts its own ring
- **Sources:** none of the three (found by the judge). **Verified** (screenshot and re-checked code).
- **Evidence:** ring shows 80.06; the same page says "0 / 4 components supported"; "Score breakdown" lists all four as "Unavailable". The backend also returns `observed_components` (the two real scores), but `frontend/src` has **zero references** to it (re-checked).
- **Fix:** when the score is observed, render `observed_components` in the breakdown and say "2 of 4 components; emergency preparedness and payment readiness withheld because …".

#### C-09 · Copilot chat is slow or falls back to the template
- **Sources:** R1 #5. Judge J-15 (**not reproduced by the judge**, to avoid sending data to Gemini). **Verified by the main assistant** (live measurements this session).
- **Evidence:** live chat answered in 34–41 s with `504 DEADLINE_EXCEEDED` warnings before the template reply; a tiny Gemini test call with `gemini-3.8-flash` returned 503 "high demand", while `gemini-3.1-flash-lite` answered in 0.5 s (one sample each; load varies). The template fallback is correct and safe.
- **Fix:** set `GEMINI_MODEL=gemini-3.1-flash-lite` in Render; lower the Gemini timeout from 30 s to about 8 s; decide which Copilot ships (branch `feature/ai-copilot` conflicts with Member 3's); optional `COPILOT_PROVIDER=offline` for instant replies.

#### C-10 · Developer and backend wording still visible
- **Sources:** R2 FP-04 (full list, debug-flag idea), R3 P0.3 (ready replacement wording), R3 P1.3. Judge J-10. **Partial**: mostly fixed in the merged UI.
- **Old build:** "CONFIGURED MONGODB", profile UUID subtitle, `moving_average_28`, "legacy v1", "Engineering diagnostics" (`forecast_unvalidated ? forecast`, …).
- **Still present in the merged UI:**
  - eyebrow `{context.as_of} · {context.data_source}` (`ConnectedDashboard.tsx:148-150`, re-checked), from `backend/app/db/factory.py`;
  - forecast-assumption lines from `intelligence/backend_adapter.py:112-116` ("Variable-spending method: moving_average_28", "Backend category vocabulary differs from PNC training data…", "…engineering-audit findings remain relevant");
  - economic details showing `scripts.refresh_intelligence` (`EconomicIntelligence.tsx` about 437–441);
  - raw ids in scenario and exposure names (see C-15).
- **Fix:** map `data_source` to "Demo data" or drop it; rewrite the adapter strings using R3's replacement table; hide `provider_errors` behind `?debug=1`.

### P2 — polish and explainability

| ID | Finding | Sources | Status | Root cause and fix |
|---|---|---|---|---|
| **C-11** | Forecast chart hides its key finding: two date labels only, odd y-ticks (`$311.76 / $2,637.88 / $4,964.00`), minimum not marked, buffer line unlabeled, no hover tooltip in code | R2 FP-07; judge J-18 | Verified (both builds) | `ConnectedDashboard.tsx` about 18–74: ticks are `[bottom, mid, top]` with `bottom = min(all values, buffer)`. Fix: round ticks, weekly date ticks, a marker "Nov 17 · $358.50", a "$500 buffer" label. |
| **C-12** | Stress band is lopsided, and table columns "Low stress / High stress" read backwards | R2 FP-07; R3 P1.3; FUTURE-IMPROVEMENTS #6; judge J-19 | Verified | Upper edge equals balance with **zero variable spending** (Nov 11 high $900 = $2,400 − $1,500 rent). `intelligence/forecasting.py` about 95–96. Fix: rename to "Higher spending (stress)" and "No variable spending"; consider a symmetric band. |
| **C-13** | Forecast and alerts omit the facts needed to explain them | R3 P0.1, P1.6, P1.7; R2 FP-07; judge J-20, J-31 | Partial: explainability gap is real; "discontinuity defect" is not (see section 5) | (a) The Nov 17 to Nov 18 jump ($358.50 to $2,418.02) is the **$2,100 biweekly paycheck** minus about $40.48 of spend. Per-day `income` and `bills` are computed in `project_cash` but dropped by the `ForecastPoint` schema (`date, projected_balance, low, high, predicted_spend`). Fix: add `income`/`bills` (or `events[]`) in the adapter and baseline, then annotate chart and table. (b) Alert numbers are in the API but not rendered: `first_breach_date 2026-11-14`, `projected_low`, `buffer`, `months_covered 1.05` (`ConnectedDashboard.tsx` about 311–317). Fix: render `alert.numbers`. |
| **C-14** | Emergency-savings alert lacks coverage, target and gap; definition inconsistent | R3 P1.2; FUTURE-IMPROVEMENTS #7; judge J-30 | Verified (applies to legacy v1 only) | v1 divides by total outflows (1.05 months); baseline and v2 use essentials (1.38). Fix with C-07 and C-13b: one definition, show months covered, target (3) and gap. The backend copy already says a transfer does not increase combined reserves. |
| **C-15** | What-if scenarios shown as raw ids (`essential cost increase`, `variable rate payment`); no "cut discretionary spending" scenario | R1 #12, #3; judge J-25 | Verified | `EconomicIntelligence.tsx` about 784–798 uses `replace(/_/g," ")` on ten ids; `economic-simulate` is a different engine from `/api/simulate`. Fix: plain labels with one-line explanations; add the spending cut (C-03). |
| **C-16** | Overview score card shows only a number and one sentence | R3 P0.2; R2 FP-05; judge J-09 | Verified; R3's P0 rating overstated | `/api/dashboard` returns only `health_score: number`. Resolve together with C-07: link to the Health Score page and show components. |
| **C-17** | Caveat block and repeated disclaimers crowd the top of the page | R2 FP-06; R3 P1.4; judge J-16 | Partial | Measured panel: 184 px (old) and 107 px (merged); first KPI tile about 374 px below the header (old) and 342 px (merged). R2's 215 px and 320 px were close. Fix: one slim banner plus a details drawer; keep contextual warnings near their features. |
| **C-18** | "Powered by Netlify" badge covers content | R2 FP-09; judge J-26 | Verified; **site B only** | Netlify injects a HUD script (`/.netlify/scripts/hud?variant=public`, free tier; re-checked) that draws a fixed badge (about 202×64 px at x=852, y=650 at 1054×714). Site A has no such script; no app code renders it. Fix: check Netlify settings or claim the site; add bottom padding. |
| **C-19** | Floating Copilot button overlaps right-edge content | R1 #10; judge J-27 | Verified; **merged UI only** | `.copilot-floating` is fixed (48×48 at x=982, y=646 at 1054). Fix: right and bottom padding on the main content, or a smaller offset. |
| **C-20** | Forecast wording: Alex's forecast uses a rolling-average fallback, not LightGBM | R1 #13; FUTURE-IMPROVEMENTS #2; judge J-32 | Verified | `forecast_reliability.method = "moving_average_28"`; the training-support check rejects Alex's spending pattern. Do not claim ML drives the live forecast. |
| **C-21** | Local checks do not reproduce production | R1 (local numbers); judge J-43, J-44 | Verified, with a correction (section 8) | A Mac without `libomp` falls back to a different forecast (low $367.08 vs $358.50 live) and shows a "Some insights are temporarily unavailable" banner. `DATA_SOURCE=demo` still uses configured database URLs from `.env` (documented, but worded confusingly). Fix: `brew install libomp` or verify on Linux; clarify docs or add an explicit generated-data mode. |
| **C-22** | Nessie service not created or verified | R1 #8; judge J-33 | **Unverified** (no Render access) | Sandbox customer and schedules file exist; the story works locally on Nessie data. A Nessie error at startup stops that service by design. See `NESSIE-PLAN.md`. |
| **C-23** | No meta description (SEO 90); title and language fixed only on site B's `index.html` and the merged build | R1 #11; judge J-34 | Partial | Lighthouse numbers match R1. Add a `<meta name="description">` to `frontend/index.html`. |

### P3 — housekeeping and unconfirmed items

| ID | Finding | Sources | Status |
|---|---|---|---|
| **C-24** | `mongodb` is many commits ahead of GitHub and unpushed; reconcile the two Copilots | R1 #14; judge J-35 | Verified |
| **C-25** | 15 backend tests fail on Macs without `libomp` (198 pass); expected to pass on Linux, unverified | R1 #15; judge J-36 | Verified on this Mac (re-run repeatedly) |
| **C-26** | `~/.npm` has root-owned files; npm suggests `sudo chown -R 501:20 ~/.npm`. Not required | R1 #16 | Verified by the main assistant (npm error text) |
| **C-27** | `.env` files hold many keys. None is tracked in git (scanned earlier); keep it that way | R1 #17 | Partial (judge did not inspect `.env` by rule) |
| **C-28** | Health Score form fields are blank, though imported facts could prefill them | R2 FP-05; judge J-23 | Partial: merged UI makes the form optional and collapsed, with imported hints; `economic_intelligence.py` already infers the values |
| **C-29** | About 300 px of blank space in the Overview score card | R2 FP-05; judge J-24 | **Unverified** (plausible grid stretch next to the 8-row category card) |
| **C-30** | Sidebar highlighted the wrong item once | R2 FP-10; judge J-28 | **Unverified**, not reproduced; likely a hover or focus artifact |

## 4. Already fixed in the merged UI (confirm after deploying it)

These were real in the old build and are gone in the merged build; they only matter if the old UI stays deployed.

| ID | Finding | Source | Evidence |
|---|---|---|---|
| F-1 | Literal "?" between diagnostic code and label (`forecast_unvalidated ? forecast`) | R2 FP-04; R3 P0.3 | A literal ASCII `?` in `ReliabilityNotices.tsx:25` (source typo, probably a lost arrow), not an encoding bug. Diagnostics are removed from default view. |
| F-2 | Header avatar "FinPilot demo" vs "Welcome, Alex Rivera" | R2 FP-04 | Hard-coded in the old bundle; merged uses `context.user.name`. |
| F-3 | AI Co-Pilot chat box buried about 1,283 px down | R2 FP-03 | Merged puts chat first for that page (textarea top at about 323 px). |
| F-4 | Stress-simulation inputs look like plain text | R2 FP-08; R1 #12 | Real `<input type=number>` with no border or background in the old build (R2's "spans or hidden fields" was wrong); merged styles them and shows only the relevant field. |
| F-5 | Two date formats (header "11/8/2026" vs ISO dates) | R2 FP-11 | Old header only; merged has no header date. One `toLocaleString()` remains for "Last bank-data sync" and shows only with Nessie data. |

## 5. Design suggestions (not defects)

| ID | Suggestion | Source | Assessment |
|---|---|---|---|
| D-1 | Reduce disclaimer repetition | R3 P1.4 | Fair editorial point; the merged UI already cut some. Overlaps C-17. |
| D-2 | Group assets and liabilities more clearly | R3 P1.1 | Arithmetic is correct. The merged UI adds hints but now shows "Credit cards $420" and "Liabilities owed $420" as two tiles, which is redundant. |
| D-3 | Re-order the dashboard hierarchy | R3 P1.5 | Reasonable redesign proposal. |
| D-4 | Ground the Copilot in user data | R3 P1.9 | **Premise largely already met:** a tool registry over the user's profile and server-rendered evidence exist (`app/routes/chat.py`, `app/tools/registry.py`, `intelligence/copilot.py`). Answer quality is untested. |
| D-5 | Add historical spending comparisons | R3 P2.0 | New feature; `/api/transactions` exists to support it. |

## 6. Claims removed or corrected

| Claim | Report | Verdict | Why |
|---|---|---|---|
| "Unexplained discontinuity" in the forecast (Nov 17 to 18) is a calculation concern | R3 P0.1 | **Incorrect as a defect** | It is the $2,100 paycheck on 2026-11-18 (`PAY_AMOUNT = 2100`, biweekly). Only the explanation is missing (C-13). |
| Move the daily forecast table into an expandable section | R3 P1.6 | **Incorrect premise** | Already a collapsed `<details>` (`ConnectedDashboard.tsx:389-415`, re-checked). |
| Organize forecast assumptions into an expandable section | R3 P1.3 | **Incorrect premise** | Already a collapsed `<details>` (lines 381-388, re-checked). The real problems are the backend wording (C-10) and the stress-band explanation (C-12). |
| Health Score is a distinct page; AI Co-Pilot differs only at the bottom | R2 FP-01 table | **Incorrect** (old build) | Four economic pages are text-identical except the heading; R2 sampled mid-load. |
| Stress inputs are "plain spans or hidden fields" | R2 FP-08 | **Incorrect** | Real number inputs without styling. |
| Cold-start of the Render service explains the slow loads | R2 FP-02 | **Not supported today** | `/healthz` answered in 0.26 s; slowness reproduced warm (compute). |
| Data is refetched "per route" | R2 FP-02 | **Corrected** | Refetched per component remount (C-05). |
| Copilot is not grounded in data | R3 P1.9 (implied) | **Unsupported** | See D-4. |
| Score transparency is a P0 | R3 P0.2 | **Overstated** | Downgraded to P1 for C-07/C-08 and P2 for the card (C-16). |
| Deployed site has a placeholder title and invalid language | R1 #2, #11 | **Outdated for site B** | Site B's `index.html` was patched; its JavaScript is still old (C-01). |
| "Only the heading changes" across the four economic pages | R1 #6 | **Overstated for the merged UI** | Panel order and subtitles also change; true for the old build. |
| Floating-button overlap is a deployed-site finding | R1 #10 | **Scope corrected** | Exists only in the merged UI (C-19). |

## 7. Contradictions between reports, resolved by evidence

1. **Four economic pages: one page or distinct?** R1 and the judge's text comparison say identical (old build); R2 saw Health Score mid-load. Resolved: identical in the old build; same component with reordered panels in the merged build (C-04).
2. **Wrapped: a dashboard copy (R2) or a story page (R1)?** Both are true, for different builds.
3. **Cause of "Unavailable" economic tiles:** R1's missing snapshot is right (re-checked); R2's "feed not configured or null" describes the symptom (C-06).
4. **Forecast jump:** R2's paycheck explanation is right; R3's "investigate the calculation" is wrong (C-13).
5. **Severity disagreements:** economic data R1 P2 vs R2 High, set P1; Guardian simulate R3 P1 vs R1 P0, set P0; score transparency R3 P0, set P1/P2.
6. **Measurements:** R2's 215 px caveat block and about 320 px first tile differ from measured 184 px and about 374 px (likely margins); conclusion unchanged.

**Spot-checks I re-ran myself on the judge's high-impact claims (all confirmed):** both sites serve the same JavaScript hash; `.gitignore:21` ignores the economic snapshot folder and the folder is missing; the Health Score page averages only supported components and the frontend never reads `observed_components`; `Promise.all` at `EconomicIntelligence.tsx:218-220`; forecast table and assumptions already collapsed; the eyebrow still prints `data_source`; live `POST /api/simulate` result.

## 8. Corrections to the judge's evaluation

| Judge item | Correction |
|---|---|
| J-43 (second point): `DATA_SOURCE=demo` "did not force demo data" | Not a defect. The setup doc says demo mode **preserves** the existing database URLs (`docs/FRONTEND_INTEGRATION.md` lines 32–33), and `build_repo` uses MongoDB, then Postgres, then generated data. The doc's wording ("runs without a database") is confusing, which is a documentation issue (C-21). It also means earlier local runs from the `mongodb` folder may have read the database named in that folder's `.env`; the demo data is the same either way. |
| J-44: demo numbers "will move after redeploy" (score 77.5 vs 75.4) | The gap is explained by the `DEFAULT_MONTHLY_BUDGET=1100` setting on Render (adds the fifth health factor), not by the redeploy. Keep that setting when redeploying. The forecast method and low value (358.50 vs 367.08) still differ on a Mac without `libomp`. |
| J-15, J-36, J-37 marked unverified | The main assistant has direct evidence: chat latency and Gemini probes (C-09), the test results (C-25) and the npm error text (C-26). Status upgraded; the judge's note that it did not re-run them stands. |

## 9. Not verified

- Copilot answer quality and reply content (nobody tested live Gemini conversations in a browser).
- Render and Netlify dashboards: instance plan, whether the Nessie service exists, Netlify badge settings (C-18, C-22).
- The merged UI deployed against the merged backend on **Linux** (all merged-UI numbers so far come from a Mac with the fallback forecast).
- Blank space in the score card (C-29) and the sidebar highlight (C-30).
- Behavior with the API down (error states), keyboard-only use, hover tooltips (none exist in the chart code), mobile drawer behavior beyond screenshots.
- Line numbers not marked "re-checked" come from the judge and were not individually re-opened.

## 10. Recommended fix order

| Step | Items | Effort | Notes |
|---|---|---|---|
| 1. Make the deploy safe | C-02 (push and redeploy backend), then C-01 (rebuild and drop frontend); set the Gemini model (C-09 setting); keep `DEFAULT_MONTHLY_BUDGET`; run the economic snapshot and commit it (C-06) | about 45 min | Backend first, always. |
| 2. Show the story | C-03 "Test this fix"; render alert numbers (C-13b) | 1–2 h | Core of the pitch. |
| 3. Make scores credible | C-07, C-08, C-14, C-16; wording clean-up C-10 | 1–2 h | Needs Member 3 for score definitions. |
| 4. Remove the "unfinished" feel | C-04 (distinct or hidden routes), C-05 (shared data, skeletons, backend cache) | 2–3 h | |
| 5. Polish | C-11, C-12, C-13a, C-15, C-17, C-18, C-19, C-20, C-23 | 2+ h | |
| 6. Housekeeping | C-21, C-22, C-24 to C-30 | as time allows | |

## 11. Retest checklist (after steps 1–3)

- [ ] Served JavaScript hash differs from `12f84b60adfa2699` and the title reads "FinPilot".
- [ ] `GET /api/financial-inputs` returns 200 on the live backend; Health Score shows no "Not Found".
- [ ] A Guardian alert has a "Test this fix" control; the result shows a low of about $508.50 for the $150 scenario.
- [ ] Economic Lab shows dated indicator values, or one empty state.
- [ ] Overview and Health Score show the same score, or clearly labelled different measures, and the breakdown lists the components behind the number.
- [ ] No raw identifiers (`moving_average_28`, `CONFIGURED MONGODB`, `scripts.refresh_intelligence`) in the default view.
- [ ] Each sidebar item has distinct first-screen content.
- [ ] Re-run the Lighthouse and browser checks on the deployed site.

## Appendix: ID map (original to consolidated)

| Judge | Consolidated | Judge | Consolidated |
|---|---|---|---|
| J-01 | C-01 | J-23 | C-28 |
| J-02 | C-02 | J-24 | C-29 |
| J-03 | C-03 | J-25 | C-15 |
| J-04 | C-04 | J-26 | C-18 |
| J-05 | C-05 | J-27 | C-19 |
| J-06 | C-06 | J-28 | C-30 |
| J-07 | C-07 | J-29 | F-5 |
| J-08 | C-08 | J-30 | C-14 |
| J-09 | C-16 | J-31 | C-13 |
| J-10 | C-10 | J-32 | C-20 |
| J-11 | F-1 | J-33 | C-22 |
| J-12 | F-2 | J-34 | C-23 |
| J-13 | F-3 | J-35 | C-24 |
| J-14 | F-4 | J-36 | C-25 |
| J-15 | C-09 | J-37 | C-26 |
| J-16 | C-17 | J-38 | C-27 |
| J-17 | D-1 | J-39 | D-2 |
| J-18 | C-11 | J-40 | D-3 |
| J-19 | C-12 | J-41 | D-4 |
| J-20 | C-13 | J-42 | D-5 |
| J-21 | removed (section 6) | J-43 | C-21 |
| J-22 | removed (section 6); wording in C-10 and C-12 | J-44 | C-21 (corrected, section 8) |
