# Workspace and assessment form update

## Implemented

- Replaced the static demo shell in `frontend/src/App.tsx` with a compact connected
  workspace. Removed the mission banner, decorative sidebar treatment and unused
  hardcoded sample screens. Sidebar is 196px wide, with compact and mobile modes.
- Moved Wrapped to a floating bottom-left shortcut. Profile shows the scoped
  customer's name and source, with a working accounts link. Notifications fetch
  current Guardian alerts when opened; they are not browser push notifications.
- Checking, savings, loans, cards and net-worth tiles open keyboard-accessible
  account details. Each imported account is separate; no bank name, mortgage type,
  interest rate or repayment term is invented. Missing fields are labeled unknown.
  APR fractions are converted to percentages. All-account totals subtract debts
  rather than adding liabilities to cash. Filtering to liabilities shows amounts owed.
- Health Score starts with an accessible circular 0–100 score. Missing totals stay
  unavailable. Editing inputs hides the old score and clears obsolete simulations.
  Score colors use disclosed 25-point display bands, not validated risk categories.
- Economic indicators use labeled colors based on the count of existing descriptive
  pressure signals: green none, yellow one, orange two, red three or more; gray
  unavailable. This is a presentation change, not a new model or market prediction.
- Digital Twin places scenario controls and results before inputs and economic
  indicators. Only the parameter fields applicable to the selected scenario appear.
  Health, Economic Lab and Copilot use their own ordering of the same connected panels.
- Payment-calendar details show the bills actually used in simulations. Form values
  do not silently rewrite imported banking records or create new payment dates.

## Assessment errors

The screenshot's $2,000 accessible-savings assumption exceeds the $600 imported
savings total. The backend correctly rejects that input. Previously the error was
displayed at the top of a long page, away from the Calculate button; the unchanged
withheld score below made the calculation appear broken.

The form now checks imported constraints, explains errors beside the relevant
field and focuses a local error summary. Structured `field_errors` accompany
domain validation failures; standard Pydantic errors are also parsed. Busy states,
an inline success message and a View assessment button make results discoverable.
Inputs are disabled while their request is running to prevent stale results from
overwriting newer edits.

The screenshot also declares $1,500 in required debt payments. If only $185 has
dated schedules, correcting savings alone does not establish complete payment
readiness: the total score remains withheld until missing payment dates are
provided. The UI explains the undated amount. Users should enter actual obligations,
not lower them to force a score. Existing score formulas and safeguards are preserved.

## Backend contract changes

- `GET /api/financial-inputs`: scoped imported savings, essential/discretionary
  minimum budgets, recorded debt schedules, normalized scheduled income and bills.
  Expense minimums round upward to cents so a displayed minimum is sufficient for
  recurring weekly amounts (e.g. $800 + $2 × 30/7 requires $808.58, not $808.57).
- Assessment/resilience/simulation domain 422 responses retain string `detail`
  and add a field-name/message map when the invalid field is identifiable.
- Account and dashboard account objects optionally include `apr`, `min_payment`
  and `credit_limit`. APR is an annual fractional rate in the existing domain model.
- No banking writes, score redefinition, training or model replacement.

## Verification

- Full Python suite: **206 passed, 1 skipped**. Required intelligence check:
  **70 passed** (overlaps the full suite).
- Frontend typecheck and production build passed.
- Full offline browser suite: **11 passed**. Additional focused workspace checks
  cover account filtering/net-worth arithmetic, profile/alerts, invalid savings,
  undated debt withholding, successful assessment/simulation and mobile navigation.
- Desktop (1440×960) and mobile (390×844) screenshots were inspected. The mobile
  browser test checks horizontal overflow. Account dialogs support Escape and
  native modal focus behavior.
- The first browser run had 10 passes and one failure because the redesigned
  net-worth tile's action icon changed an exact-text locator. The label is now a
  separate semantic span; the full rerun passed without changing the financial assertion.

Live Nessie browser verification was not performed in this update: automatic
approval review could not launch the live-data server because it reported an
account usage limit. Testing continued against a local, explicitly fictional
fixture; those results do not establish live connector compatibility.

For repeatable offline verification:

```powershell
.venv/Scripts/python.exe -m scripts.serve_ui_fixture
```

In another terminal:

```powershell
cd frontend
$env:FINPILOT_API_TARGET='http://127.0.0.1:8001'
npm.cmd run dev -- --host 127.0.0.1 --port 5174
```

The fixture uses no banking API keys, no .env repository configuration and no paid
LLM requests. For normal use, restart the regular backend and frontend with the
configured local environment; the backend restart is required for the new route.
