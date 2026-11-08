# FinPilot Frontend — Investigative Report & Fix Guide

Nov 8, 2026 · @Abhishek

> Report #2 (pasted by Abhishek and saved as received; the first report is [INVESTIGATION-REPORT.md](INVESTIGATION-REPORT.md)). Root causes below are hypotheses from a live click-through, not confirmed in code.

## Summary

FinPilot's numbers are correct and its caveats are honest, but the app feels unfinished: most of the nine routes repeat another screen, several load slowly with nothing on screen, and developer text shows through. Fix FP-02, FP-01 and FP-03 before the hackathon demo; the rest is polish. Eleven issues were found.

| ID | Severity | Where | Problem | Fix in one line |
|---|---|---|---|---|
| FP-01 | High | My Finances, Guardian, Wrapped, Digital Twin, Economic Lab, AI Co-Pilot | Routes repeat another route's content | Build distinct views or hide the route |
| FP-02 | High | Guardian, Wrapped, Health Score, first load | Bare "Loading…" line for about 3 to 10 s; no skeleton; data refetched per route | Shared cache, skeletons, cold-start message, keep backend warm |
| FP-03 | High | Digital Twin, Economic Lab, AI Co-Pilot | Every indicator "Unavailable"; chat box buried at the bottom | Fixture data, one empty state, chat first |
| FP-04 | Medium | Dashboard routes | Database name, profile ID, snake_case labels, "legacy", diagnostics and a name mismatch visible | Debug flag and plain labels |
| FP-05 | Medium | Dashboard, Health Score | Two scores; 77.5 / 100 beside high-severity alerts; blank card; form not prefilled | One score, prefill, breakdown |
| FP-06 | Medium | Dashboard routes | 215 px caveat block above all content | Slim banner plus drawer |
| FP-07 | Medium | Forecast chart | Two date labels, low point unmarked, confusing band and column names | Ticks, marker, renamed columns |
| FP-08 | Medium | AI Co-Pilot | Stress-simulation inputs look like plain text | Real inputs with units and a visible result |
| FP-09 | Low | Every route | Netlify badge covers content | Check site settings; add bottom padding |
| FP-10 | Low | Sidebar | Wrong item highlighted once | Derive from the route |
| FP-11 | Low | Header, bills, forecast | Two date formats | One date formatter |

**Suggested order.** FP-02 first, because a cold backend can make the demo look broken. Then FP-01 and FP-03, which decide whether judges see a complete product. FP-04 and FP-06 are quick wins that remove clutter. FP-05, FP-07 and FP-08 improve the story the product tells. FP-09 to FP-11 are cleanup.

## Environment and method

Every finding comes from a live click-through of the deployed prototype on 8 Nov 2026 (about 08:00 US Central), not from the source code. Treat root causes as hypotheses to confirm in the repo.

| Item | Detail |
|---|---|
| Frontend | https://mellow-brigadeiros-9dbbfa.netlify.app/ — single-page app on Netlify with hash routing: /#/overview, /#/my-finances, /#/forecasts, /#/health-score, /#/guardian, /#/digital-twin, /#/economic-lab, /#/ai-co-pilot, /#/finpilot-wrapped |
| Backend | https://finpilot-o0gj.onrender.com — GET /api/dashboard, /api/context, /api/forecast?days=30 |
| Browser | Desktop Chrome, viewport 1054 × 714 px, sidebar open |
| Data | Synthetic demo profile; the page's own "as of" date is 2026-11-07 |
| Inspected | All 9 routes, visual layout, accessibility tree, network calls, collapsed sections expanded |
| Not inspected | Source code, Lighthouse or performance traces, mobile widths and the "Open navigation" drawer, keyboard-only use, behavior after pressing action buttons (Reload analysis, Run hypothetical scenario, Ask with confirmed inputs, Calculate assessment, 7/90-day toggles), API-down error states |
| Console | No errors or warnings recorded, but logging started after the first page load |

**Working well — do not regress while fixing:**

- The numbers reconcile. Net worth $2,580 = checking $2,400 + savings $600 − card balance $420. The eight spending categories sum to $2,846, matching the Spending tile.
- The honesty copy is good: "planning estimate", "not a credit score", "not financial advice", "synthetic prototype". Keep it, but move it (see FP-07).
- Semantics are better than they look: the page has main, navigation, a labelled region ("Data and forecast reliability") with an alert, and the chart is exposed as an image with alt text. The sidebar and header buttons carry text labels.

## What the app looks like

Nine sidebar routes exist, but only about four distinct screens sit behind them: the dashboard, the forecast card, the health-score form, and the economic-conditions page. The descriptions below are what a sighted tester sees at 1054 × 714 px.

**Shell (on every route).** A dark navy theme with teal accents. A fixed sidebar about 243 px wide holds the teal arrow logo with "FinPilot" and the tagline "SEE DEEPER. ACT SMARTER.", then nine icon links in this order: Overview, My Finances, Forecasts, Health Score, Guardian, Digital Twin, Economic Lab, AI Co-Pilot, FinPilot Wrapped. The active link is a rounded pill with a teal outline and tint. At the foot of the sidebar are a teal dot with "Synthetic prototype / Data status appears in the dashboard" and a "Collapse sidebar" button. The top bar shows "MISSION: FINANCIAL FREEDOM" in a condensed display font with the subtitle "A 360° financial health navigator". On the right are a calendar icon with "11/8/2026", a bell with an orange dot, and an avatar "FP" labelled "Welcome back / FinPilot demo". A floating pill, "Powered by Netlify", sits bottom-right above the page content.

**Overview, top to bottom.**

- Small teal eyebrow "2026-11-07 · CONFIGURED MONGODB"; H1 "Welcome, Alex Rivera"; grey subtitle "Synthetic financial prototype · 00000000-0000-4000-8000-00000000a1e5 · not financial advice"; a "Reload analysis" button at the top right.
- One rounded card, about 215 px tall, with an amber left-bordered warning: "This is a planning estimate. Its accuracy has not been validated for this spending pattern." Under it are two collapsed disclosure rows, "Data limitations · 1" and "Engineering diagnostics".
- Six tiles in a 3 × 2 grid: Net worth $2,580.00, Checking $2,400.00, Savings $600.00, Liabilities owed $420.00, Inflow · last 30 days $4,200.00, Spending · last 30 days $2,846.00. The first tile row starts roughly 320 px down the page.
- Two cards side by side. Accounts: Everyday Checking $2,400.00, Rewards Card (credit card, owed) $420.00, Savings $600.00. Upcoming bills · 14 days: Rent 2026-11-11 $1,500.00, Utilities 2026-11-13 $120.00, Streaming 2026-11-15 $16.00.
- Two more cards side by side. Spending by category · 30 days lists rent $1,500, groceries $446, dining $332, entertainment $252, utilities $120, transportation $96, shopping $84, subscriptions $16. Financial health · legacy v1 shows "77.5 / 100" and two lines of grey caveat text, then about 300 px of empty card, because it stretches to the height of its neighbour.
- "Guardian · 30-day outlook": two amber-bordered alerts. "Low Balance · high" says projected checking falls below the chosen buffer. "Emergency Savings · medium" says liquid reserves cover fewer than three months of modeled outflows.
- "Predictive spending & cash flow": a 7 / 30 / 90 day segmented control (30 selected, solid teal), a method line, three figures (Ending checking $3,747.24; Lowest projected checking $358.50 on 2026-11-17; Safety buffer $500.00), a teal line chart with a shaded band and a dashed red buffer line, a one-line legend, and two collapsed rows, "Forecast assumptions" and "Daily forecast · 30 days".

**Route by route.**

| Route | What is on screen | Distinct from Overview? |
|---|---|---|
| Overview | The full dashboard above, H1 "Welcome, Alex Rivera" | — |
| My Finances | H1 "My Finances", then the same warning card, tiles, cards, Guardian outlook and forecast, in the same order | No, same content (checked at top, middle and bottom) |
| Forecasts | H1 "Forecasts", the warning card, then the Predictive spending & cash flow card | Yes, a subset; not checked below the card |
| Health Score | Eyebrow "VERSIONED FINANCIAL INTELLIGENCE", H1 "Health Score", the line "Loading economic evidence and profile…", then a "Confirm financial inputs" form: six empty fields (take-home income, essential cash expenses, discretionary cash expenses, required debt payments, accessible emergency savings, variable-rate debt), two unchecked confirmation boxes, and a "Calculate assessment" button | Yes |
| Guardian | H1 "Guardian", then the same dashboard as Overview | No, same content (checked at top, middle and bottom) |
| Digital Twin | Same eyebrow as Health Score, a card "No reported data limitations.", then "Economic conditions · 2026-11-07" with the headline "Insufficient Data" and tiles Headline CPI, Core CPI, PCE, Unemployment, Federal funds, 10y… all reading "Unavailable" | Yes, but identical to Economic Lab and AI Co-Pilot at the top; the bottoms were not compared |
| Economic Lab | Same as Digital Twin at the top; bottom not compared | See above |
| AI Co-Pilot | Same economic page, then at the bottom: "Economic stress simulation" (a dropdown "essential cost increase", plain text "Percentage assumption10", "Dollar assumption 1000", "Delay days7", and a "Run hypothetical scenario" button) and "Ask FinPilot with this assessment" (a textarea with placeholder "What does inflation mean for me?" and an "Ask with confirmed inputs" button) | Yes, only by what sits at the very bottom |
| FinPilot Wrapped | H1 "FinPilot Wrapped", then the same dashboard as Overview. No recap or story-style content was seen | No, same content (checked at top, middle and bottom) |

## Issue details

Each issue lists what a tester sees, the evidence, a likely cause (a hypothesis until confirmed in code), a suggested fix and an acceptance test. IDs match the summary table.

### FP-01 · High · Most routes show the same screen

**What you see.** My Finances, Guardian and FinPilot Wrapped each render the entire Overview dashboard under a different H1: same warning card, same six tiles, same cards, same forecast. Digital Twin, Economic Lab and AI Co-Pilot open on the same "Economic conditions" page. Wrapped contains no recap or story content, and Guardian has no dedicated view, only one card at the bottom of the dashboard.

**Evidence.** Screenshots at the top, middle and bottom of My Finances, Guardian and Wrapped matched Overview card for card. The three economic routes matched at the top (checked) but their bottoms were not compared.

**Likely cause.** The routes map to one or two shared page components with only the title swapped.

**Fix.** For each route, build it or hide it. A minimal split that fits the existing components: My Finances = accounts, bills, categories; Guardian = outlook alerts plus the forecast; Wrapped = a short recap (top category, largest bill, lowest-balance date, score); Digital Twin = the stress simulation; Economic Lab = indicators; AI Co-Pilot = chat only. Anything not ready is removed from the sidebar or marked "Coming soon", never duplicated.

**Done when.** No two routes share the same first screen, each sidebar label matches its content, and the AI Co-Pilot input is visible without scrolling.

### FP-02 · High · Blank loading screens and a slow first response

**What you see.** Opening Guardian or FinPilot Wrapped shows an almost empty dark page with one small line at top left, "Loading your financial snapshot…". There is no skeleton or spinner. It stayed that way for between about 3 and 10 seconds. Health Score shows "Loading economic evidence and profile…" above a form that is already on screen, so the page looks half-loaded.

**Evidence.** In the first network capture, GET /api/dashboard and GET /api/forecast?days=30 were still pending while /api/context had returned 200. On a later reload all three returned 200 within about 8 seconds. Routes visited earlier in the session rendered instantly; first visits showed the loading line, which suggests data is requested per route rather than shared.

**Likely cause.** The Render service is probably spinning down when idle, so the first request waits for a cold start (a hypothesis; confirm the plan type). There is also no shared data store or cache across routes.

**Fix.** (1) Before any demo, ping the API or move to an always-on instance. (2) Fetch once in a shared provider and reuse it across routes, refreshing in the background. (3) Show skeleton cards shaped like the real layout. (4) After about 8 seconds, show "Waking the server, this can take up to a minute" with a Retry button. (5) Add an error state for failed requests; none was tested.

**Done when.** Every route paints a skeleton within 100 ms, a cold start shows the waking message, a failed request shows an error with Retry, and navigating between visited routes never shows the loading line again.

### FP-03 · High · Economic data is empty and the AI Co-Pilot is buried

**What you see.** Digital Twin, Economic Lab and AI Co-Pilot show the headline "Insufficient Data", "Pressure breadth: Unavailable / 100", and every indicator tile (Headline CPI, Core CPI, PCE, Unemployment, Federal funds, 10y…) reading "Unavailable". On AI Co-Pilot the real controls, a stress simulation and an "Ask FinPilot" box, sit below about three screens of these empty tiles.

**Evidence.** Same result on all three routes, after waiting several seconds. The page states its as-of date as 2026-11-07, so this is not a still-loading state.

**Likely cause.** The economic-indicator feed is not configured or returns nulls for that date. Check the /api/context response before assuming anything else.

**Fix.** Seed fixture values for demo mode so the tiles show numbers. When a feed is genuinely down, replace the wall of tiles with one empty state that gives the reason and a "last updated" time. Move the Ask box to the top of AI Co-Pilot.

**Done when.** With fixtures on, every tile shows a value and a date. With the feed off, one empty state appears instead of a dozen "Unavailable" tiles. The chat input is visible without scrolling.

### FP-04 · Medium · Developer and database text is visible to users

**What you see.** Strings meant for engineers appear in the interface:

- Eyebrow above the H1: "2026-11-07 · CONFIGURED MONGODB".
- Subtitle: "Synthetic financial prototype · 00000000-0000-4000-8000-00000000a1e5 · not financial advice", which exposes a profile ID.
- "Estimate method: moving_average_28" above the forecast.
- Card title "Financial health · legacy v1".
- The "Engineering diagnostics" disclosure, which lists forecast_unvalidated, legacy_score_partial, "Serving baseline has no applicable independent real-customer validation." and a prototype-score note.
- "Forecast assumptions" lines such as "Backend category vocabulary differs from PNC training data; inference may use a warned baseline fall…" and "Synthetic prototype; original engineering-audit findings remain relevant."
- The Overview H1 reads "Welcome, Alex Rivera" while the header avatar says "FinPilot demo".

**Evidence.** The text was read from the page's accessibility tree. In that tree the diagnostics lines show a ? between the code and its label (for example forecast_unvalidated ? forecast). I did not confirm visually what that glyph is; check for an encoding problem or a missing arrow icon.

**Fix.** Put engineering diagnostics and database or ID text behind a debug flag (for example ?debug=1). Replace identifiers with plain labels such as "Forecast method: 28-day average". Use one persona name everywhere.

**Done when.** In default mode no snake_case identifier, UUID, database name or the words "legacy" and "engineering" appear anywhere, and the name in the H1 matches the header.

### FP-05 · Medium · Two health scores that disagree, and an empty score card

**What you see.** The dashboard card "Financial health · legacy v1" shows a comfortable-looking "77.5 / 100". Directly below, Guardian raises a high-severity low-balance alert and a medium emergency-savings alert. The separate Health Score route runs a different, versioned assessment and asks the user to type six figures the dashboard already knows (income, essential and discretionary spending, debt payments, emergency savings, variable-rate debt). The dashboard score card has no gauge or breakdown, and about 300 px of it is blank because it stretches to match the neighbouring card.

**Fix.** Keep one score. Prefill the Health Score form from the loaded profile (the dashboard shows $4,200 inflow and $2,846 spending over 30 days) and compute on load. Retire the legacy card or label it a preview. Show the components that make up the score, and show the cash-risk level beside the number so the score and the alerts tell one story.

**Done when.** The dashboard and the Health Score route show the same number, the form opens prefilled, and no card is more than 40% blank.

### FP-06 · Medium · The caveat block crowds the top of every dashboard page

**What you see.** A bordered card holding an amber warning plus two disclosure rows sits above all content and is about 215 px tall. At 1054 × 714 px the first KPI tiles start roughly 320 px down, so the numbers a user came for sit near the fold.

**Fix.** Replace it with a one-line banner of 40 px or less ("Planning estimate, not validated" plus a Details link). Open "Data limitations" in a popover or drawer. Move Engineering diagnostics behind the debug flag from FP-04. The honest wording stays.

**Done when.** The first KPI row starts within 160 px of the top of the content area and the limitations are still one click away.

### FP-07 · Medium · The cash-flow chart hides its own key finding

**What you see.** The 30-day chart is a teal line over a shaded band with a dashed red buffer line, roughly 600 × 150 px. The line drops from about $2,400 to a trough, then jumps sharply back up and drifts down again.

- The x-axis has two labels only: "2026-11-08" and "2026-12-07". Nothing marks Nov 11 (rent) or Nov 17 (the low).
- The y-axis has three odd ticks: $4,964.00, $2,637.88 and $311.76. The bottom tick is the lowest stress value, not a round number.
- The headline finding, lowest projected checking $358.50 on 2026-11-17, below the $500 buffer, appears only as text. The dashed buffer line sits about 6 px above the chart floor, so the dip below it is nearly invisible.
- The shaded band is lopsided. Its upper edge equals the balance with zero variable spending: day 1 shows $2,400.00 (the opening balance), and Nov 11 shows $900.00 (that is, $2,400 minus $1,500 rent). Its lower edge is the "Low stress" column.
- In the "Daily forecast" table the column names are backwards for a reader. "Low stress" holds the lower balance, which is the high-spending case, and "High stress" holds the higher balance.

**Evidence.** Values read from the daily table: Nov 16 checking $398.83, Nov 17 $358.50, Nov 18 $2,418.02. The jump is a paycheck of about $2,100 (2,418.02 − 358.50 + 40.48 daily spending = 2,100.00). Variable spending is about $40 a day throughout. The hover tooltip was not tested.

**Fix.** Add weekly date ticks and round money ticks. Mark the minimum with a dot and a label ("Nov 17 · $358.50"). Label the buffer line "$500 buffer" and tint the area below it. Rename the table columns to "Lower bound" and "Upper bound" (or "Higher spending" and "No variable spending") and confirm with the backend owner that a zero-spending upper edge is intended. Link the chart to its table for screen readers.

**Done when.** The chart alone shows when and by how much balance falls below the buffer, tick labels are readable at 1054 px, and the column names match what the numbers mean.

### FP-08 · Medium · The stress-simulation inputs render as plain text

**What you see.** On AI Co-Pilot, "Economic stress simulation" has a dropdown set to "essential cost increase". Below it, three items are laid out in an uneven row and look like unstyled text, not form fields: "Percentage assumption10" (label and value touch), "Dollar assumption 1000" (wrapped onto two lines) and "Delay days7". No input boxes, units or bounds are visible. A "Run hypothetical scenario" button follows, with no visible results area.

**Evidence.** Seen at the bottom of the page at 1054 px wide. I did not click into the values or press the button, so I cannot say whether they are editable or what the output looks like.

**Likely cause.** The inputs are missing styles, or they are plain spans or hidden fields inside a label.

**Fix.** Use real labelled number inputs with units (%, $, days), sensible min and max, and helper text. Disable the button until the inputs are valid, and show the result directly under it.

**Done when.** Each assumption is a visible, keyboard-focusable field with a label that does not touch its value, and a run produces a visible result.

### FP-09 · Low · A floating badge covers page content

**What you see.** A dark pill reading "Powered by Netlify" (about 175 × 34 px) is fixed to the bottom-right corner of the viewport. On first load it covers the end of the "Upcoming bills · 14 days" heading, so it reads "14 day". At the bottom of a page it sits over the corner of the last card.

**Cause.** The badge is injected by Netlify, not by the app's own markup as far as I can tell.

**Fix.** Check the Netlify site settings for the badge or toolbar, and look at the production domain before the demo. Either way, add at least 56 px of bottom padding to the scrolling content area so nothing important ends under a fixed overlay.

**Done when.** The last card on every route can be scrolled fully clear of the corner.

### FP-10 · Low · Sidebar highlight once showed the wrong item

**What you see.** On #/overview, after scrolling, "FinPilot Wrapped" was highlighted and Overview was not. The URL still read #/overview. A fresh load later highlighted Overview correctly, and every other route highlighted correctly, so this was not reproduced.

**Likely cause.** The active state may be driven by hover or focus rather than by the route alone, or it may fall out of step with the hash.

**Fix.** Derive the active item only from the current route and keep it in sync on back, forward and reload. Test with the browser history buttons.

**Done when.** After any sequence of navigation, the highlighted item always matches the route.

### FP-11 · Low · Dates appear in two formats

**What you see.** The header shows "11/8/2026", which a reader outside the US could take as 11 August. Bills, the forecast and the eyebrow use ISO dates such as "2026-11-11".

**Fix.** Use one shared date formatter across the app, for example "Nov 8, 2026".

**Done when.** Every visible date uses the same format.

## Not yet tested, and a retest checklist

This review did not cover the areas below, so a clean retest of the fixes should include them.

**Not covered.** Mobile and tablet widths, including the "Open navigation" drawer that exists in the markup. Keyboard-only use and focus order. What happens after pressing Reload analysis, Calculate assessment, Run hypothetical scenario, Ask with confirmed inputs, and the 7 and 90 day buttons. Hover tooltips on the chart. The bottom of Digital Twin and Economic Lab (only AI Co-Pilot's bottom was seen). Anything below the forecast card on the Forecasts route. Behavior when the API is down. Lighthouse scores and bundle size. Console output during the first page load.

**Retest checklist.**

- [ ] Let the backend sit idle for 15 minutes, then open Guardian cold. A skeleton or a "waking the server" message appears within a second or two; no bare text line.
- [ ] Visit all nine routes in order, then again. The second pass never shows a loading screen.
- [ ] Compare the first screen of every route. No two are the same.
- [ ] Search the rendered page for _-separated identifiers, UUIDs, "MONGODB", "legacy" and "engineering". None appear in default mode.
- [ ] The H1 name matches the header name on every route.
- [ ] Dashboard score equals the Health Score route's score, and the Health Score form opens prefilled.
- [ ] At 1054 × 714 px the first KPI row is visible without scrolling past a caveat block.
- [ ] The forecast chart shows weekly date ticks, a labelled marker at the Nov 17 low, and a labelled $500 buffer line.
- [ ] The stress-simulation fields are visible inputs with units, and running the scenario shows a result.
- [ ] With the API blocked, each route shows an error message and a Retry button.
- [ ] At 390 px wide, the sidebar becomes a drawer and no card overflows horizontally.
- [ ] Tab through the header and sidebar with the keyboard; focus is always visible.
- [ ] The "Powered by Netlify" badge, if it remains, never hides content.
- [ ] Back, forward and reload keep the correct sidebar item highlighted.
