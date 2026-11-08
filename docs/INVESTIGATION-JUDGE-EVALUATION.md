> Saved copy of the independent judge's output, unedited apart from this note. Consolidated result: [INVESTIGATION-REPORT-CONSOLIDATED.md](INVESTIGATION-REPORT-CONSOLIDATED.md). Evidence files referenced below live in a temporary scratch folder and may not persist.

# Judge evaluation of the three FinPilot investigation reports

Date: 2026-11-08. Judge: independent, read-only. Reports evaluated:
R1 `docs/INVESTIGATION-REPORT.md` (items 1-17), R2 `docs/INVESTIGATION-REPORT-2.md` (FP-01..FP-11), R3 `docs/INVESTIGATION-REPORT-3.md` (P0.1..P2.0).

Evidence folder: `/private/tmp/claude-501/-Users-abhishek-Desktop-Claude-FinPilot/45259878-e4eb-4d2e-b887-df771ff61dbe/scratchpad/judge/`
(`siteB/` = site B walk + crops, `merged-local/` = merged UI against merged backend run locally, `walk.mjs`, `crops.mjs`, downloaded bundles `*.js/*.css`, API captures `fc-*.json`, `db-*.json`, `ctx-*.json`, `res-*.json`, `fi-*.json`, `oa-*.json`, `backend.log`). All servers I started were stopped.

## 0. The most important context: which build each report saw

| Fact | Evidence |
|---|---|
| **Site B serves the same old UI as site A.** Both serve `/assets/index-4GkFAzox.js` and `/assets/index-CW7iX1HS.css`. The SHA-256 hashes are identical (JS `12f84b60…2063`, 279,410 bytes; CSS `507ac646…da7f`). | `judge/boisterous-cassata-005b39.js` vs `judge/mellow-brigadeiros-9dbbfa.js` |
| Site B's `index.html` alone was patched: `<title>FinPilot</title>`, `lang="en"`, `/favicon.png`. Netlify also injects `<script src="/.netlify/scripts/hud?variant=public" data-account-tier="free">`, which draws the "Powered by Netlify" badge. Site A's `index.html` keeps `<!-- figma:title -->`/`<!-- figma:lang -->` and has no HUD script. | `judge/*.index.html` |
| The merged UI (`frontend/dist`, `index-0bUWSgu-.js`, `index-kq9UnrCP.css`; the same CSS as `scratchpad/dist-local`) is a **different** bundle. It has 8 sidebar items, and Wrapped moved to a floating "FinPilot Wrapped" button. It has no header date, a "Workspace / <page>" breadcrumb, and an avatar built from `context.user.name`. | `App.tsx:36-45,179-187,197-222` |
| Old-build markers, from the bundle and from the site-B walk: 9 sidebar items including "FinPilot Wrapped"; header "MISSION: FINANCIAL FREEDOM", `new Date().toLocaleDateString()` → "11/8/2026"; hard-coded avatar "FP / Welcome back / FinPilot demo"; "Financial health · legacy v1"; "Engineering diagnostics"; UUID subtitle; no `/api/financial-inputs` call; no Wrapped component (Wrapped renders `ConnectedDashboard`). The source matches commits `8ab7112`/`origin/gokul` (e.g. `ReliabilityNotices.tsx` at `8ab7112`). | `siteB/walk.json`, `siteB/01-overview.png` |
| Live backend `finpilot-o0gj.onrender.com`: `/api/financial-inputs` returns **404**, and `/api/demo/savings-stress` is not in its OpenAPI. The merged backend lists both. | `judge/oa-live.json`, `judge/oa-local.json`, `fi-live.json` |

Consequence: **every R2 finding is about the old UI**, and so is R1's site-A diagnosis. R3 says only "deployed Overview". Its quoted strings (`legacy v1`, `forecast_unvalidated ? forecast`) prove it also saw the old UI. Many differences between the reports come down to old UI vs merged UI. They are not real disagreements.

## 1. Summary table

Verdict key: VERIFIED, PARTIALLY verified, UNVERIFIED, INCORRECT, BUILD-SPECIFIC (true only for one build), DESIGN SUGGESTION. Severity: P0 breaks or blocks the demo, P1 hurts the demo, P2 polish, P3 housekeeping.

| ID | Title | Reports | Verdict | Sev |
|---|---|---|---|---|
| J-01 | Both Netlify sites serve the old first-drop UI | R1 #2 (R2 env, R3 implicit) | VERIFIED (corrected) | P0 |
| J-02 | Live backend older than merged code; `/api/financial-inputs` 404 breaks merged Health/Twin/Lab/Co-Pilot | R1 #1 | VERIFIED | P0 |
| J-03 | No Guardian → `/api/simulate` "test this fix" flow | R1 #3, R3 P1.8 | VERIFIED | P0 |
| J-04 | Several routes render the same content | R1 #6, R2 FP-01 | VERIFIED (per-build detail) | P1 |
| J-05 | Slow first paint, bare "Loading…" text, no shared data cache | R1 #4, R2 FP-02 | VERIFIED | P1 |
| J-06 | Economic indicators all "Unavailable" | R1 #9, R2 FP-03 | VERIFIED (root cause found) | P1 |
| J-07 | Two health scores disagree (77.5 vs 80.06) | R1 #7, R2 FP-05, R3 P0.2 | VERIFIED | P1 |
| J-08 | Health Score page: ring shows 80.06 but "Score breakdown" lists all four components "Unavailable" / "0 / 4 supported" | none (new) | VERIFIED | P1 |
| J-09 | Overview score card has no component breakdown | R3 P0.2, R2 FP-05 | VERIFIED | P2 |
| J-10 | Developer / database text visible to users | R2 FP-04, R3 P0.3, R3 P1.3 (partly) | PARTIALLY (mostly fixed in merged; remainder persists) | P1 |
| J-11 | "?" between code and label in diagnostics | R2 FP-04, R3 P0.3 | BUILD-SPECIFIC (literal "?" in source) | P3 |
| J-12 | Header "FinPilot demo" vs H1 "Alex Rivera" | R2 FP-04 | BUILD-SPECIFIC (fixed in merged) | P3 |
| J-13 | AI Co-Pilot chat box buried under economic tiles | R2 FP-03 | BUILD-SPECIFIC (fixed in merged) | — |
| J-14 | Stress-simulation inputs look like plain text | R2 FP-08 (R1 #12 quotes "Percentage assumption10") | BUILD-SPECIFIC (fixed in merged) | — |
| J-15 | Copilot chat slow / falls back to template | R1 #5 | UNVERIFIED by judge | P1 |
| J-16 | Caveat block crowds top of dashboard | R2 FP-06 | PARTIALLY (old 184 px; merged 107 px) | P2 |
| J-17 | Disclaimer repetition | R3 P1.4 | DESIGN SUGGESTION | P3 |
| J-18 | Forecast chart: odd y-ticks, 2 date labels, minimum unmarked, buffer unlabeled | R2 FP-07 | VERIFIED (both builds) | P2 |
| J-19 | Stress band upper edge = zero variable spending; "Low/High stress" column names misleading | R2 FP-07, R3 P1.3 | VERIFIED | P2 |
| J-20 | Nov 17 → Nov 18 jump unexplained; per-day income/bill events not exposed | R3 P0.1, R3 P1.6, R2 FP-07 | PARTIALLY (explainability gap real; "discontinuity defect" wrong) | P2 |
| J-21 | Daily forecast table "overemphasized" | R3 P1.6 | INCORRECT | — |
| J-22 | Forecast assumptions need a dedicated expandable section | R3 P1.3 | PARTIALLY (already collapsed; wording is the real issue) | P2 |
| J-23 | Health Score form not prefilled | R2 FP-05 | PARTIALLY / BUILD-SPECIFIC | P3 |
| J-24 | ~300 px blank space in score card | R2 FP-05 | UNVERIFIED | P3 |
| J-25 | Raw scenario names; no "cut discretionary spending" scenario | R1 #12, R1 #3 | VERIFIED | P2 |
| J-26 | "Powered by Netlify" badge covers content | R2 FP-09 | BUILD-SPECIFIC (site B deployment only) | P2 |
| J-27 | Floating Copilot button overlaps right-edge content | R1 #10 | BUILD-SPECIFIC (merged UI only), verified | P2 |
| J-28 | Sidebar highlighted wrong item once | R2 FP-10 | UNVERIFIED | P3 |
| J-29 | Two date formats (header 11/8/2026 vs ISO) | R2 FP-11 | BUILD-SPECIFIC (old header only) | P3 |
| J-30 | Emergency-savings alert lacks coverage numbers; definition inconsistent | R3 P1.2 | VERIFIED | P2 |
| J-31 | Insights don't say why/when ("below $500 on Nov 14") | R3 P1.7 | PARTIALLY (data already in API, not rendered) | P2 |
| J-32 | Forecast method wording: Alex is not on LightGBM | R1 #13 | VERIFIED | P2 |
| J-33 | Nessie service not running anywhere | R1 #8 | UNVERIFIED | P2 |
| J-34 | SEO / lang / title (Lighthouse) | R1 #11 | PARTIALLY | P3 |
| J-35 | Git: `mongodb` unpushed; reconcile Copilots | R1 #14 | VERIFIED | P3 |
| J-36 | 15 Mac test failures from missing libomp | R1 #15 | PARTIALLY | P3 |
| J-37 | `~/.npm` root-owned files | R1 #16 | UNVERIFIED | P3 |
| J-38 | Secrets in `.env` | R1 #17 | UNVERIFIED (not inspected by rule) | P3 |
| J-39 | Net-worth / asset-liability presentation | R3 P1.1 | DESIGN SUGGESTION | P3 |
| J-40 | Weak dashboard hierarchy | R3 P1.5 | DESIGN SUGGESTION | P3 |
| J-41 | AI Co-Pilot should be grounded in data | R3 P1.9 | DESIGN SUGGESTION (premise largely already met) | P3 |
| J-42 | Historical spending comparisons | R3 P2.0 | DESIGN SUGGESTION | P3 |
| J-43 | Local Mac runs don't reproduce production numbers (LightGBM fallback, `.env` DB override) | none (new) | VERIFIED | P2 |
| J-44 | Demo numbers will change after redeploy (score 77.5 → ~75.4 locally; forecast method changes) | none (new) | PARTIALLY | P2 |

**Totals: 44 distinct issues.** VERIFIED 16, PARTIALLY 9, UNVERIFIED 6, INCORRECT 1, BUILD-SPECIFIC 7, DESIGN SUGGESTION 5.

## 2. Measured facts used below

Walk at 1054×714 (R2's viewport), sidebar clicks via hash change, Chrome 157 headless. "readyMs" = time until no "Loading/Calculating" text.

| Route (order visited) | Site B (old UI, live backend) | Merged UI + merged backend (local, Mac) |
|---|---|---|
| Overview (first) | 5,451 ms | 1,037 ms |
| My Finances | 161 (no refetch) | 159 |
| Forecasts | 160 | 160 |
| Health Score | 1,146 | 972 |
| Guardian | **6,371** (refetch after leaving dashboard component) | 658 |
| Digital Twin | 1,151 | 973 |
| Economic Lab / AI Co-Pilot | 160 | 160 |
| Wrapped | 5,074 (refetch; old Wrapped = dashboard) | story page |
| Overview again (from Wrapped) | 160 (same component) | 552 (refetch; remount) |

Live API now: `/api/dashboard` and `/api/forecast` each ~3.0 s alone (curl) and 4.6–6.4 s in parallel in the browser. `/api/context` ~0.8–1.0 s, `/api/resilience` ~1.1 s. The local merged backend serves each in ~0.6 s.

---

## 3. Per-issue detail

### J-01 · Both Netlify sites serve the old UI · VERIFIED (corrected) · P0
- Reports: R1 #2. R2 and R3 used the old build without knowing it.
- Evidence: identical JS/CSS hashes on site A and site B (section 0). Site B `index.html` was hand-patched (title, lang, favicon) but still loads `index-4GkFAzox.js`.
- Correction to R1: R1's evidence ("placeholder `<title>` and invalid language") is true for site A only. Site B has a valid title and `lang="en"` but the **same old JavaScript**. R1 #11's "deployed site still has [invalid lang]" is likewise outdated for site B.
- Root cause: Netlify Drop of a `dist` built from pre-redesign source. Site B is the same bundle with a new `index.html`.
- Fix: rebuild `frontend/` from `mongodb` with `VITE_API_BASE=https://finpilot-o0gj.onrender.com` and drop it on the site to be demoed, after J-02. Confirm `index-0bUWSgu-.js` (or a newer hash) is served.
- Severity rationale: every other UI fix is invisible until this is done.

### J-02 · Live backend is older; merged UI breaks on 4 pages · VERIFIED · P0
- Reports: R1 #1.
- Evidence: `GET /api/financial-inputs` returns 404 on live and 200 locally. Live OpenAPI lacks `/api/financial-inputs` and `/api/demo/savings-stress`. `EconomicIntelligence.tsx:218-231` does `Promise.all([resilience, financial-inputs])`. One 404 rejects both, so `context` is never set and the page shows the FastAPI detail ("Not Found") while every panel stays empty. This affects Health Score, Digital Twin, Economic Lab and AI Co-Pilot (`App.tsx:286`). The notifications "Simulate spending 90% of savings" button would also fail (`App.tsx:115`).
- Fix (R1's fix is right): push `mongodb` and Manual Deploy on Render **before** J-01. Optional hardening: use `Promise.allSettled` so the Health page renders without `financial-inputs`.

### J-03 · No Guardian → simulate flow · VERIFIED · P0
- Reports: R1 #3 (strongest: names the endpoint, scenario and numbers), R3 P1.8 (product framing, says "reduce by $100").
- Evidence: no `/api/simulate` call anywhere in `frontend/src` (grep). Only `economic-simulate` (`EconomicIntelligence.tsx:307`) and `demo/savings-stress` (`App.tsx:115`) are called. The Guardian alert carries `suggested_scenario {type: spending_cut, reduction_amount: 150, horizon_days: 10}` (`db-live.json`). A read-only `POST /api/simulate` with that scenario returned 200 on **live: low $358.50 → $508.50, end $3,747.24 → $3,897.24, score 77.51 → 79.87**. On the merged backend run locally it returned $367.08 → $517.08 (Mac fallback, see J-43). The what-if list (`EconomicIntelligence.tsx:784-795`) has 10 stress types and no spending cut.
- Fix: in `ConnectedDashboard.tsx` Guardian section (lines 307-322), when `a.suggested_scenario` exists, render "Test this fix" → `post("simulate", {scenario: a.suggested_scenario})` and show baseline vs scenario `projected_low`. Add a `simulate` result type to `api.ts`.
- Severity: this is the core demo story. R3's P1 is too low if the pitch relies on it.

### J-04 · Duplicate routes · VERIFIED · P1
- Reports: R1 #6, R2 FP-01.
- Evidence, old build (site A/B, bundle router `["Economic Lab","Health Score","Digital Twin","AI Co-Pilot"].includes(active) ? EconomicIntelligence : ConnectedDashboard`). Rendered text compared with the H1 removed:
  - Overview = My Finances = Guardian = FinPilot Wrapped (identical except H1).
  - Forecasts = subset (warning + forecast card).
  - **Health Score = Digital Twin = Economic Lab = AI Co-Pilot** (identical except H1; 3,583-3,584 chars each).
- Merged UI (`App.tsx:284-290`, `EconomicIntelligence.tsx:928-935,942-950`):
  - Overview = My Finances = Guardian (identical except H1, verified).
  - Forecasts = subset.
  - The four economic pages use one component with the **same six panels in a different order** and a different subtitle. AI Co-Pilot puts chat first; Health Score puts the score ring first.
  - Wrapped is a real story page (`FinPilotWrapped.tsx`).
- Corrections:
  - R2's table says Health Score is distinct and AI Co-Pilot differs "only by what sits at the bottom". Both are **incorrect** for the old build: the four pages are identical. R2 saw Health Score mid-load. The old component renders the input form before the economic panel arrives (site B first screen on AI Co-Pilot during load: "Loading economic evidence and profile… Confirm financial inputs…").
  - R1's "only the heading changes" is correct for the old build. For the merged UI it overstates the problem slightly: panel order and subtitle also change.
- Fix: R2's split proposal is the most concrete. Minimum for the demo: give Guardian its own view (alerts + simulate from J-03) and hide My Finances, or make it accounts/bills only via `page` checks in `ConnectedDashboard.tsx`.

### J-05 · Slow loads, bare loading text, no shared cache · VERIFIED · P1
- Reports: R1 #4 (timings, Lighthouse, server cause), R2 FP-02 (UX symptoms, fix list).
- Evidence: timings in section 2. No skeleton or spinner anywhere (grep `skeleton|spinner` in `frontend/src` finds nothing). Loading states are plain `<p role="status">` (`ConnectedDashboard.tsx:125,341`, `EconomicIntelligence.tsx:961`).
- Data fetching:
  - State lives inside each page component (`ConnectedDashboard.tsx:85-116`, `FinPilotWrapped.tsx:67-70`, `EconomicIntelligence.tsx:216-232`). No provider caches dashboard/forecast.
  - `/api/context` is fetched by `App.tsx:74`, by `ConnectedDashboard` and by `FinPilotWrapped`, so up to 3 times.
- Nuance neither report states: data is **not** refetched per route. It is refetched per component **remount**. Overview → My Finances → Forecasts reuse one `ConnectedDashboard` instance (160 ms). Going to any economic page and back remounts it and costs another 5-6 s on live (Guardian 6,371 ms). R2's statement that routes visited earlier render instantly holds only within one component family.
- Backend: live `/api/dashboard` and `/api/forecast` each take ~3 s alone and ~5-6 s when parallel, consistent with R1's single-worker, duplicate-computation explanation (`app/services/dashboard.py` runs guardian + health; the forecast endpoint recomputes the forecast). Cold start was not observed: `/healthz` answered in 0.26 s, so slowness is compute, not sleep. R2's cold-start hypothesis is plausible but not what made today's runs slow.
- Best fix: combine R1 and R2.
  - Frontend: a shared data provider (React context keyed by `as_of`) holding dashboard/forecast/context for `ConnectedDashboard` and `FinPilotWrapped`, plus skeletons (R2).
  - Backend: memoize per profile+as_of for 30-60 s (R1).
  - Operations: keep the pinger, pre-open pages.

### J-06 · Economic indicators "Unavailable" · VERIFIED (root cause) · P1
- Reports: R1 #9 (cause right: FRED snapshot missing on Render), R2 FP-03 (hypothesis: feed not configured or nulls; better UX fix).
- Evidence: live and local `/api/resilience` both return `economic_conditions.status = "Insufficient Data"`, `indicators: []`, all features null, and `provider_errors: {"cache": "Run python -m scripts.refresh_intelligence"}`.
- Code path: `backend/intelligence/economic_data.py:15-16` reads `ROOT/data/economic_snapshots/latest.json` (`cached()`, lines 157-170). The directory does not exist in the repo. `.gitignore:21` ignores `data/economic_snapshots/` (and `:20` `data/economy/fred.csv`). Snapshots are only created by the CLI `scripts/refresh_intelligence.py` (network fetch, FRED key). So this is a **missing, git-ignored snapshot file**, not a null feed and not a missing fixture.
- Severity: R1 says P2, R2 High. I set P1, because three of eight pages lead with a wall of "Unavailable".
- Fix:
  - Run `python -m scripts.refresh_intelligence` once, commit a dated snapshot (un-ignore one file, e.g. `data/economic_snapshots/latest.json`) or bake it into the Render build.
  - UI: one empty state instead of 8 "Unavailable" tiles (R2).

### J-07 · Two health scores disagree · VERIFIED · P1
- Reports: R1 #7, R2 FP-05 (best description), R3 P0.2 (transparency angle). None found the real root cause.
- There are **three** score implementations:
  1. Overview card = `dashboard.health_score` ← `app/services/health.py` → gateway `intelligence.health_score.compute_health_score` → legacy v1 `intelligence/health_score.py:5-30`. Emergency = (checking + savings) / **total** monthly outflow (line 12). Live value 77.51; merged backend run locally 75.36.
  2. Baseline fallback `app/baseline/health.py:48-61`: emergency = liquid / **essential** spending (90 days).
  3. Health Score page = `/api/resilience` → `app/services/economic_intelligence.py:25-51`. It infers facts from imported data, then `observed_score` = weighted mean of **only the supported components** (line 39-40). For Alex only Cash-flow sustainability (60.91) and Debt-payment affordability (99.22) are supported. Emergency preparedness and Payment readiness are None. (60.91 + 99.22)/2 = **80.06**.
- Why the numbers differ: v2's 80.06 **omits emergency savings entirely**, the weakest area that Guardian flags. Legacy v1 includes it. The higher number is less complete, not "better".
- R3 claim check ("emergency savings should use essential expenses"): baseline and v2 already use essentials. Legacy v1 (which drives the Overview number and the Guardian emergency alert, `intelligence/guardian.py:28-31`) uses total outflows. This matches FUTURE-IMPROVEMENTS #7 (1.05 vs 1.38 months). Partially correct, and it applies only to legacy v1.
- Fix: decide one headline score.
  - Show v2 on Overview (from `/api/resilience` or add `observed_score` to `/api/dashboard`), with its confidence and "2 of 4 components".
  - Or label the Overview card clearly as a different measure.
  - Owners: Member 3 (backend), Member 1 (`ConnectedDashboard.tsx:301-305`).

### J-08 · Health Score breakdown contradicts the ring · VERIFIED · P1 (no report found this)
- Evidence: screenshot `judge/merged-local/health-score-top.png` shows "80.06 / 100" with "Confirmed-input assessment: 0 / 4 components supported". "Score breakdown" (`EconomicIntelligence.tsx:674-717`) renders `health.components`, the confirmed-input components, all `score: null`. The backend also returns `observed_components` (`economic_intelligence.py:51`), with the two real scores, but nothing in `frontend/src` reads it (grep).
- Fix: when `scoreIsObserved`, render `health.observed_components` in the breakdown and say "2 of 4 components; emergency preparedness and payment readiness withheld because …".

### J-09 · Overview score card lacks components · VERIFIED · P2
- Reports: R3 P0.2, R2 FP-05.
- Evidence: old card "Financial health · legacy v1 / 77.5 / 100 / Internal heuristic…". Merged card `ConnectedDashboard.tsx:301-305` shows "Financial health snapshot", a number and one sentence. `/api/dashboard` returns only `health_score: number`; components are available from `/api/financial-health` (v2) or the legacy result inside the service.
- Correction: R3's P0 is overstated. Missing explanation does not break the demo. Resolve it together with J-07 (a link to the Health Score page plus the components).

### J-10 · Developer text exposure · PARTIALLY (mostly fixed in merged) · P1
- Reports: R2 FP-04 (most complete list), R3 P0.3 (good replacement wording table), R3 P1.3.
- Old build (verified in site-B text and bundle): eyebrow "CONFIGURED MONGODB", UUID subtitle, "Estimate method: moving_average_28", "legacy v1", "Engineering diagnostics" with `forecast_unvalidated ? forecast` etc., backend assumption lines.
- Merged UI:
  - Removed: UUID (subtitle now "Your accounts, cash flow…"), "legacy v1" (now "Financial health snapshot"), "Engineering diagnostics" (`ReliabilityNotices.tsx` renders only critical and data-limitation messages).
  - Mapped: the method label (`ConnectedDashboard.tsx:11-16`).
- Still exposed in the merged UI:
  - Eyebrow `{context.as_of} · {context.data_source}` (`ConnectedDashboard.tsx:148-150`) → "CONFIGURED MONGODB". The string comes from `backend/app/db/factory.py:25,37`.
  - "Forecast assumptions" lines come straight from the backend: `intelligence/backend_adapter.py:112-116` ("Variable-spending method: moving_average_28.", "Backend category vocabulary differs from PNC training data…", "…engineering-audit findings remain relevant.").
  - Economic details show `cache: Run python -m scripts.refresh_intelligence` (`EconomicIntelligence.tsx:437-441`).
  - Raw scenario ids (J-25) and exposure ids `a.id.replace(/_/g," ")` (line 747).
- Fix: drop `data_source` from the eyebrow (or map it to "Demo data"); rewrite the `backend_adapter.py` assumption strings in plain language (R3's table); hide `provider_errors` behind `?debug=1`.

### J-11 · The "?" glyph · BUILD-SPECIFIC · P3
- Evidence: commit `8ab7112` `frontend/src/ReliabilityNotices.tsx:25` contains the literal ASCII `{n.code} ? {n.context}`, and the shipped bundle contains `` ` ? ` ``. It is **not** a runtime encoding bug. It is a literal question mark in source, probably an arrow lost in the author's editor. Gone in the merged UI.
- R2 asked whether it was an encoding problem or a missing icon. Answer: neither at runtime; it is a source typo. R3 quotes it verbatim without comment.

### J-12 · Avatar name mismatch · BUILD-SPECIFIC · P3
- Old bundle hard-codes "FP / Welcome back / FinPilot demo". Merged `App.tsx:110,123-128,216-219` uses `context.user.name` ("AR / Alex Rivera"). Fixed.

### J-13 · Chat buried on AI Co-Pilot · BUILD-SPECIFIC
- Old build: the chat textarea sat ~1,283 px down. Merged: `panelOrder` puts chat first for AI Co-Pilot (`EconomicIntelligence.tsx:933-934`); textarea top at 323 px. Fixed.

### J-14 · Stress inputs look like plain text · BUILD-SPECIFIC
- Old build: computed style of the three stress inputs is `background: rgba(0,0,0,0)`, `border: 0px`, 24 px tall (`siteB/walk.json`; crop `siteB/stress-sim.png` shows "Percentage assumption10"). They **are** real `<input type=number>` with min/max (bundle). R2's guess "plain spans or hidden fields" is wrong; "missing styles" is right.
- Merged: styled input (bg `rgb(26,34,48)`, 1 px border, 42 px), label above value, and only the field relevant to the chosen scenario is shown (`EconomicIntelligence.tsx:801-852`; crop `merged-local/stress-sim.png`). Fixed.

### J-15 · Copilot chat slow / falls back · UNVERIFIED by judge · P1
- Reports: R1 #5, consistent with FUTURE-IMPROVEMENTS #10/#11.
- I did not send chat requests (would hit the Gemini key and send data). Code shows a server-rendered, evidence-selected reply (`intelligence/copilot.py:1-5`), so the template fallback is safe. The latency figures and model names (`gemini-3.8-flash`, `gemini-3.1-flash-lite`) remain R1's unreproduced measurements.

### J-16 · Caveat block crowding · PARTIALLY · P2
- R2 FP-06. Measured "Data and forecast reliability" panel: **184 px** on site B (R2 said ~215, which likely includes margins), first KPI tile at 444 px document Y (~374 px below the 70 px header; R2 said ~320). Merged: panel **107 px**, first tile 342 px. Improved in merged; still above the fold. Local Mac adds a second line from J-43.

### J-17 · Disclaimer repetition · DESIGN SUGGESTION · P3
- R3 P1.4. Old Overview repeats "synthetic prototype" (sidebar and subtitle), "not financial advice", "planning estimate", "not a credit score" and "not a calibrated confidence interval". This is a fair editorial point, not a defect. The merged UI already cut some of it. It overlaps J-16.

### J-18 · Chart readability · VERIFIED (both builds) · P2
- R2 FP-07 (strongest by far).
- Code: `ConnectedDashboard.tsx:18-74` is unchanged between builds.
  - Ticks are `[bottom, mid, top]` with `bottom = min(all low/high/projected, buffer)`, giving "$311.76 / $2,637.88 / $4,964.00" on live (`siteB/chart.png`).
  - Only first and last dates are labeled.
  - The buffer is an unlabeled dashed line; the minimum is not marked.
  - No hover or tooltip exists in the code (R2 did not test; there is none).
- Fix: R2's (round ticks, weekly dates, a min marker "Nov 17 · $358.50", a "$500 buffer" label).

### J-19 · Band definition and column names · VERIFIED · P2
- Evidence: live rows Nov 8-10 `high = 2400.00`, Nov 11 `high = 900.00` (2,400 − 1,500 rent), Nov 15-17 `high = 764.00` (2,400 − 1,500 − 120 − 16). The upper edge is therefore balance with **zero** variable spending. Code: `intelligence/forecasting.py:95-96` (`high += income - due - row['lower']`; the lower spend quantile is ≈0 on this path). Table headers are "Low stress" and "High stress" (`ConnectedDashboard.tsx:398-399`). "Low stress" holds the worst case. R2 is correct.
- FUTURE-IMPROVEMENTS #6 already flags that the stress envelope is not a probability band.
- Fix: rename to "Higher spending (stress)" / "No variable spending". Consider a symmetric band (e.g. ±k·σ cumulative) in `project_cash`.

### J-20 · Forecast jump unexplained · PARTIALLY · P2
- R3 P0.1 calls it a "discontinuity" to investigate. R2 FP-07 already proved it is the paycheck: 2,418.02 − 358.50 + 40.48 = **2,100.00**, matching `PAY_AMOUNT = 2100` biweekly in `backend/app/data/synthetic.py:16-17`.
- The calculation is correct, so R3's P0 framing (and "No unexplained discontinuities remain") is **incorrect**. What is real is the explainability gap. `project_cash` already computes per-day `income` and `bills` (`forecasting.py:104`), but the API schema `ForecastPoint` has only `date, projected_balance, low, high, predicted_spend` (`fc-live.json` keys; `intelligence/backend_adapter.py:104`; `app/schemas/forecast.py`).
- Fix: add `income` and `bills` (or an `events[]` list) to `ForecastPoint` in both the adapter and `app/baseline/forecast.py`, then annotate the chart and table.

### J-21 · Daily table "overemphasized" · INCORRECT
- R3 P1.6 asks to "move the detailed daily forecast into an expandable section". It already is a collapsed `<details>` ("Daily forecast · 30 days", `ConnectedDashboard.tsx:389-415`) in both builds. R2 also describes it as collapsed.

### J-22 · Forecast assumptions organization · PARTIALLY · P2
- R3 P1.3. Already a collapsed `<details>` ("Forecast assumptions", lines 381-388). The real problem is the backend wording (J-10) and the missing explanation of the stress band (J-19).

### J-23 · Form not prefilled · PARTIALLY / BUILD-SPECIFIC · P3
- R2 FP-05. Old build: a required six-field form with no score until it is filled. Merged: the score is computed automatically, the form is optional and collapsed ("Review or correct imported assumptions"), and its hints show imported values (`EconomicIntelligence.tsx:508-537`). Fields are still blank. `economic_intelligence.py:32-37` already infers those facts and could return them for prefill.

### J-24 · Blank space in score card · UNVERIFIED · P3
- R2 FP-05 (~300 px). Not measured by me. Plausible: grid stretch next to the 8-row category card. Check `connected.css` `.live-grid.two` `align-items`.

### J-25 · Raw scenario names; no spending-cut scenario · VERIFIED · P2
- R1 #12 and #3. `EconomicIntelligence.tsx:784-798`: ten snake_case ids shown via `replace(/_/g," ")`; no spending cut. `economic-simulate` is a different engine from `/api/simulate`.

### J-26 · Netlify badge · BUILD-SPECIFIC (deployment) · P2
- R2 FP-09. Verified on site B: Netlify injects a HUD script (`/.netlify/scripts/hud?variant=public`, `data-account-tier="free"`) that creates `iframe#nl-badge-frame`, fixed at x=852, y=650, 202×64 at 1054×714. It covers the right edge of the "Spending · last 30 days" tile on load (`siteB/01-overview.png`). Site A's HTML has no HUD script, and no app code renders it.
- Fix: check site B's Netlify settings (claim the site / disable the badge or toolbar), or demo from a site without it. Bottom padding in `.main-content` is a good safeguard, especially because of J-27.

### J-27 · Floating Copilot overlaps content · BUILD-SPECIFIC (merged), verified · P2
- R1 #10. Merged `.copilot-floating` is fixed at x=982, y=646, 48×48 at 1054 width and sits over the tile edges (`merged-local/01-overview.png`). Not present in the old build (0 matches in its bundle). Fix: right/bottom padding on `.main-content`, or a smaller offset.

### J-28 · Sidebar highlight · UNVERIFIED · P3
- R2 FP-10 (not reproduced by R2). Both builds derive `active` from the hash on `hashchange` (old bundle `addEventListener("hashchange", …)`; merged `App.tsx:63-71`). After scrolling, my run showed Overview active. `.nav-item:hover` uses a different (gray) style. Probably a hover/focus artefact; no evidence of a state bug.

### J-29 · Two date formats · BUILD-SPECIFIC · P3
- R2 FP-11. Old header uses `new Date().toLocaleDateString()` → "11/8/2026". The merged header has no date. Merged still uses `toLocaleString()` for "Last bank-data sync" (`ConnectedDashboard.tsx:157`), but `loaded_at` is `null` on both backends today, so it shows only with Nessie data.

### J-30 · Emergency-savings alert context · VERIFIED · P2
- R3 P1.2. The live alert payload has `numbers: {months_covered: 1.05}`, but the UI renders only title, severity, cause and action (`ConnectedDashboard.tsx:311-317`). Definition: legacy v1 total outflows (J-07).
- R3's acceptance item "do not imply a transfer increases reserves" is already in the backend copy ("a transfer alone does not increase combined liquid reserves").
- Fix: render `a.numbers` (months covered, target 3 months, gap).

### J-31 · Explainable insights · PARTIALLY · P2
- R3 P1.7. Low-balance alert `numbers: {projected_low: 358.5, buffer: 500, first_breach_date: "2026-11-14"}` is in the API and not shown. R3's example date "November 14" is exactly `first_breach_date`, and the forecast agrees (Nov 14 $495.25 < $500). Cheap fix in `ConnectedDashboard.tsx` alert rendering. Contributing events need J-20.

### J-32 · Forecast method wording · VERIFIED · P2
- R1 #13. Live `forecast_reliability.method = "moving_average_28"`. `intelligence/forecasting.py:30-44` falls back to it. FUTURE-IMPROVEMENTS #2 explains the zero-spend-fraction gate.

### J-33 · Nessie service not running · UNVERIFIED · P2
- R1 #8. Render dashboard not inspectable from here. R1's own plan keeps MongoDB as the demo source, so this is not a blocker.

### J-34 · SEO / lang / title · PARTIALLY · P3
- R1 #11. Lighthouse JSON (site A, LH 12.8.2): mobile perf 41 / a11y 95 / BP 100 / SEO 90, LCP 7.7 s; desktop 52/95/100/90, LCP 6.3 s; `meta-description` 0, `html-lang-valid` 0. All match R1.
- Site B and merged `index.html` have a valid lang and title. **Neither has a meta description**, so the SEO-90 point still applies after redeploy.

### J-35 · Git housekeeping · VERIFIED · P3
- R1 #14. `mongodb` is now 18 commits ahead of `origin/mongodb` (R1 said 15; three docs commits for the reports were added since). `origin/test` tip `a80b246` confirmed.

### J-36 · Mac tests fail on libomp · PARTIALLY · P3
- R1 #15. `import lightgbm` in the test venv fails: `libomp.dylib` not found (`/opt/homebrew/opt/libomp` absent). The 15/198 count was not re-run.

### J-37 / J-38 · npm cache, secrets · UNVERIFIED · P3
- Not inspected; `.env` reading was out of scope by instruction.

### J-39 · Net worth presentation · DESIGN SUGGESTION · P3
- R3 P1.1. The arithmetic is right. The merged UI already adds hints ("Assets minus recorded debt", "Recorded card balances owed") but now shows "Credit cards $420" and "Liabilities owed $420" as two tiles (`ConnectedDashboard.tsx:183-235`), which is redundant for Alex.

### J-40 · Hierarchy · DESIGN SUGGESTION · P3
- R3 P1.5. Reasonable redesign proposal; no defect.

### J-41 · Copilot grounding · DESIGN SUGGESTION (premise largely met) · P3
- R3 P1.9 presents grounding as missing. Code shows it exists:
  - `app/routes/chat.py:19-20` builds a `ToolRegistry` over the user's profile with tools for accounts, health, forecast, guardian, simulate, economy, resilience, economic simulation and purchase (`app/tools/registry.py:80-146`).
  - `intelligence/copilot.py:1-5`: "No … financial math is delegated to Gemini. Final output is a validated selection of server-rendered evidence."
- R3 did not test Copilot, as it says itself. Answer quality remains unverified.

### J-42 · Historical comparisons · DESIGN SUGGESTION · P3
- R3 P2.0. New feature; `/api/transactions` exists to support it.

### J-43 · Local Mac verification is not production-representative · VERIFIED · P2 (no report)
- Evidence: the merged backend run locally logs `intelligence.forecast.forecast failed (OSError)` on every forecast (`judge/backend.log`; libomp missing). The gateway falls back to baseline (`app/services/gateway.py:47-49,63-71`), giving method `weekday_mean_90`, low **$367.08** (not $358.50), a narrow ±$18 band instead of the zero-spend upper edge, and a visible critical banner "Some insights are temporarily unavailable. Showing a backup estimate." (`merged-local/01-overview.png`).
- Also, `env -u MONGODB_URI -u DATABASE_URL … DATA_SOURCE=demo` did **not** force demo data: the app still read `.env` and reported `data_source: "configured PostgreSQL"` after "MongoDB not reachable; trying next database".
- R1's local-run conclusions about the UI hold. Its local numbers (e.g. 80.06) and any J-19 band visuals do not predict Render.
- Fix: install libomp for local checks (`brew install libomp`), or verify on Linux/Render. Make `DATA_SOURCE=demo` override `.env` database URLs (`backend/app/db/factory.py`).

### J-44 · Demo numbers will move after redeploy · PARTIALLY · P2 (no report)
- Merged backend (local) Overview score 75.36 vs live 77.51 for the same profile and `as_of`. Locally, `/api/simulate` baseline `health_score` was 62.4 while `/api/dashboard` said 75.36 (possibly a Mac-fallback artefact). Any script quoting 77.5, $358.50 or $508.50 must be re-checked on the redeployed Linux backend before the demo.

---

## 4. Overlap evaluations: which report explains each issue best

| Issue | Strongest | Why |
|---|---|---|
| J-04 duplicate routes | R1 for accuracy, R2 for the fix | R1 correctly groups all four economic pages; R2 misread two routes but gives a usable per-route split. |
| J-05 loading/slowness | R1 + R2 (complementary) | R1 has measured API times, Lighthouse and the server cause; R2 has the UX symptoms and a good acceptance test. Neither saw the remount-vs-route nuance. |
| J-06 economic data | R1 cause, R2 fix | R1's "FRED snapshot not on Render" is right; R2's "fixtures + one empty state" is the better UX fix. |
| J-07 two scores | R2 description; none on root cause | R2 ties the comfortable score to the alerts; R3 adds transparency; nobody found that v2 omits emergency savings. |
| J-10 dev text | R2 list, R3 wording | R2 enumerates and proposes a debug flag; R3's replacement table is ready to use. |
| J-18/19/20 forecast | R2 | Verified arithmetic (paycheck, zero-spend edge), exact ticks, concrete fixes. R3's P0.1 is a weaker restatement. |
| J-03 Guardian simulate | R1 | Endpoint, scenario, before/after numbers; R3 is product-level only. |

## 5. Contradictions and how evidence resolves them

1. **R1 #6 vs R2 FP-01 table (Health Score / AI Co-Pilot distinct?)**
   - R1 says the four economic pages are one page. R2 says Health Score is distinct and AI Co-Pilot differs at the bottom.
   - Resolution: in the old build they are identical except the H1 (text-equal). R2 sampled Health Score while it was still loading.
2. **R2 FP-01 "Wrapped is a dashboard copy" vs R1 "real Wrapped story page"**
   - Resolution: both are true, for different builds (old vs merged).
3. **R1 #9 vs R2 FP-03 (cause of "Unavailable")**
   - Resolution: missing, git-ignored `data/economic_snapshots/latest.json`. R1 is right; R2's "feed not configured / nulls" is the symptom.
4. **R1 #2 / #11 (deployed site has placeholder title/lang) vs R2's site (has the title FinPilot)**
   - Resolution: site B has a patched `index.html` with the same old JS.
5. **R3 P0.1 ("unexplained discontinuity, investigate the calculation") vs R2 FP-07 (it is the paycheck)**
   - Resolution: R2 is right ($2,100 biweekly pay). The defect is explainability only.
6. **R3 P1.6 / P1.3 ("move table/assumptions into expandable sections") vs R2 (both already collapsed)**
   - Resolution: R2 is right (code lines 381-415).
7. **R2 FP-02 ("data requested per route") vs observation**
   - Resolution: per component remount, not per route.
8. **Severity disagreements**
   - Economic data: R1 P2 vs R2 High → judge P1.
   - Score transparency: R3 P0 vs others Medium/P1 → judge P2 for the card, P1 for J-07/J-08.
   - Guardian simulate: R3 P1 vs R1 P0 → judge P0.
9. **R2 FP-06 sizes (215 px; first tiles ~320 px) vs measured (184 px panel; tiles 444 px doc / ~374 px content)**
   - Resolution: minor measurement differences; the conclusion is unchanged.

## 6. Unsupported or incorrect claims

- R2 FP-01 table: "Health Score — Yes [distinct]" and "AI Co-Pilot — distinct only by what sits at the very bottom". **Incorrect** for the build R2 tested.
- R2 FP-08 likely cause "plain spans or hidden fields". **Incorrect**: they are real number inputs without styling.
- R2 FP-02 cold-start hypothesis. Not supported today (`/healthz` 0.26 s; slowness reproduced warm).
- R2 FP-10. Unreproduced; no supporting code path.
- R3 P0.1 implies a possible calculation defect. **Incorrect**: the paycheck is correct.
- R3 P1.6 and P1.3 "move into expandable section". **Incorrect premise**: already collapsed.
- R3 P1.9 implies the Copilot is not grounded. **Premise unsupported**: a tool registry and server-rendered evidence exist.
- R3 P0.2's P0 severity. Overstated.
- R1 #2 / #11 evidence. Outdated for site B (title and lang fixed, JS still old).
- R1 #6 "only the heading changes". True for the old build; slightly overstated for the merged UI (panel order and subtitles differ).
- R1 #10. True only for the merged UI; R1 lists it among deployed-site findings without saying so.
- R1 local-run numbers (80.06; "page loads"). Valid for UI behavior, but the forecast numbers come from a Mac fallback (J-43).
- R1 #5 latency/model numbers and #15 test count. Not reproduced by the judge.

## 7. Duplicates (same underlying issue)

| Canonical | Report IDs |
|---|---|
| J-03 | R1 #3 = R3 P1.8 |
| J-04 | R1 #6 = R2 FP-01 |
| J-05 | R1 #4 = R2 FP-02 |
| J-06 | R1 #9 = R2 FP-03 (first half) |
| J-07 | R1 #7 = R2 FP-05 (first half) = R3 P0.2 (partly) |
| J-09 | R3 P0.2 = R2 FP-05 ("no gauge or breakdown") |
| J-10 | R2 FP-04 = R3 P0.3 (+ R3 P1.3 wording part) |
| J-11 | R2 FP-04 "?" = R3 P0.3 quoted `? forecast` |
| J-14 / J-25 | R2 FP-08 ≈ R1 #12 ("Percentage assumption10" quoted; R1 focuses on names) |
| J-16 / J-17 | R2 FP-06 ≈ R3 P1.4 (same clutter, different angle) |
| J-19 | R2 FP-07 (band and columns) ≈ R3 P1.3 ("explain low/high stress") ≈ FUTURE-IMPROVEMENTS #6 |
| J-20 | R3 P0.1 = R2 FP-07 (jump evidence) = R3 P1.6 ("inspect events for a date") |
| J-30 / J-31 | R3 P1.2 and P1.7 share one fix: render `alert.numbers` |

## 8. Important things none of the reports mention

1. **Site B serves the identical old JavaScript as site A** (hash-verified). Fixing site B's title and lang did not deploy the redesign. (J-01)
2. **Health Score page breakdown contradicts its own ring**: it shows 80.06 while listing all four components as "Unavailable" and "0 / 4 supported". `observed_components` is returned but never rendered. (J-08)
3. **Why v2 reads higher**: 80.06 averages only cash-flow (60.91) and debt (99.22) and silently omits emergency savings, the very thing Guardian warns about. (J-07)
4. **Guardian alert payloads already contain** `first_breach_date: 2026-11-14`, `projected_low`, `buffer` and `months_covered: 1.05`, but the UI drops them. Cheap explainability win. (J-30/J-31)
5. **Per-day income and bills are computed in `project_cash` but dropped by the API schema**, which blocks event annotation. (J-20)
6. **Root cause of the economic outage** is the git-ignored `data/economic_snapshots/` (`.gitignore:21`), so no deploy can ever have it without an explicit step. (J-06)
7. **Local Mac verification uses a fallback forecast and a `.env` database** even with `env -u` / `DATA_SOURCE=demo`; it also shows a "Some insights are temporarily unavailable" banner the demo would not show. (J-43)
8. **Merged UI still shows "CONFIGURED MONGODB"** and backend assumption strings with `moving_average_28`, "PNC training data", "engineering-audit", plus `scripts.refresh_intelligence` in economic details. (J-10)
9. **Partial failure handling**: `Promise.all` in `EconomicIntelligence.tsx:218` makes one missing endpoint blank four pages. `allSettled` would degrade gracefully. (J-02)
10. **Demo numbers are not stable across backends**: score 77.51 live vs 75.36 merged-local. Re-check scripts after redeploy. (J-44)

## 9. Verification I could not complete

- Copilot chat latency and model behavior (J-15): not called, to avoid sending data and using the Gemini key.
- Render/Netlify dashboards (Nessie service J-33, badge settings J-26, instance plan): no access.
- Full backend test suite count (J-36): not re-run; only the libomp import failure was confirmed.
- `.env` and secrets (J-38), npm cache ownership (J-37): out of scope or not inspected.
- The merged UI deployed against the merged backend on Linux: not available. J-43/J-44 numbers come from a Mac with the LightGBM fallback.
- Score-card blank-space measurement (J-24): not measured.
