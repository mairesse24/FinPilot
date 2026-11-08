# Dashboard, forecasting and Nessie integration

The React/Vite frontend from `origin/frontend` now lives in `frontend/`. It uses
the existing FastAPI endpoints, not the standalone Member 3 CLI JSON files.
Original frontend design components and intelligence modules are retained.

## Run locally on Windows

From the repository root, start the backend:

```powershell
.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
.venv/Scripts/python.exe -m uvicorn app.main:app --app-dir backend --reload
```

In a second terminal:

```powershell
cd frontend
npm.cmd ci
npm.cmd run dev
```

Open `http://localhost:5173`. Vite forwards `/api` to `127.0.0.1:8000`; there are
no banking or LLM credentials in the browser. Start from the repository root so
the backend reads the root `.env`. Alternatively use `backend/.env` when running
from `backend/`. Do not maintain conflicting copies. A production frontend must
reverse-proxy `/api` to the deployed backend; the Vite proxy is development-only.

## Data sources

`DATA_SOURCE=demo` runs without a database or external services. Existing
`DATABASE_URL` behavior is preserved in this mode. `DATA_SOURCE=nessie` takes
precedence and imports only `NESSIE_CUSTOMER_ID` into an in-memory repository.
It never substitutes generated records after a Nessie failure: startup fails
with a sanitized error. This prototype has no user authentication. Use only
fictional sandbox records; demo user selection is not an authorization system.

```dotenv
DATA_SOURCE=nessie
NESSIE_API_KEY=your_private_key
NESSIE_CUSTOMER_ID=your_sandbox_customer_id
NESSIE_BASE_URL=https://api.nessieisreal.com
NESSIE_SCHEDULES_FILE=data/synthetic/nessie-schedules-local.json
```

List customers without writing anything:

```powershell
.venv/Scripts/python.exe -m scripts.nessie_customers
```

For an empty sandbox, preview then create a fictional customer and records:

```powershell
.venv/Scripts/python.exe -m scripts.seed_nessie
.venv/Scripts/python.exe -m scripts.seed_nessie --apply --configure
```

The explicit `--apply` creates one customer, checking/savings/card accounts, an
auto loan, a merchant, 40 historical purchases and 8 historical deposits. `--configure`
updates only the banking selection and demo date in root `.env`. No existing
customer is changed. Created resource IDs are checkpointed in ignored
`data/synthetic/nessie-local.json`; rerunning resumes rather than duplicates
successful requests. Do not delete this checkpoint and blindly rerun after an
ambiguous network failure. A remote creation may succeed before a response is
lost, so this is not server-enforced idempotency.

The API loads a snapshot at startup. Restart it to refresh bank records. The
source and load timestamp appear in the UI via `GET /api/context`.

The importer follows the [official Nessie SDK endpoint shapes](https://github.com/nessieisreal/nessie-javascript-sdk).
It reads customer/accounts and account purchases/deposits/withdrawals/loans. It
validates ownership, duplicate IDs, finite cent amounts and completed statuses;
future-dated activity is excluded. Balance snapshots are authoritative and are
not reconstructed from partial transaction histories.

Current limits are visible in the UI: only checking activity enters cash-spending
history; savings, card activity, ATM cash and internal transfers are excluded.
Card balances count as liabilities. Approved loans count as liabilities only
when the customer-bound schedule file supplies their confirmed remaining
principal in `loan_balances`, keyed by loan ID. The original loan `amount` is
not assumed to be remaining debt. Missing balances generate a warning; pending
or declined applications are excluded. Payment dates still require explicit
bills. These fields follow the [official Nessie loan model](https://github.com/nessieisreal/nessie-ios-sdk/blob/master/Nessie-iOS-Wrapper/Loan.swift).
Nessie net worth covers imported accounts only. Historical deposits are inflows, not
proof of salary. Unknown purchase categories map to `other`. The dashboard is
therefore a view of modeled/imported data, not a full financial ledger.

## Schedules and categories

Historical deposits do not prove future payroll dates. Future income and bills
are explicitly supplied by a customer-bound JSON file. The seed command writes
a clearly synthetic schedule. An example shape is:

```json
{
  "customer_id": "your_sandbox_customer_id",
  "income": [{"name":"Demo pay","amount":2100,"frequency":"biweekly","date":"2026-11-18"}],
  "bills": [{"name":"Demo rent","amount":1500,"frequency":"monthly","date":"2026-11-11","category":"rent"}],
  "transaction_categories": {"purchases:historical-rent-id":"rent"},
  "loan_balances": {"your-approved-loan-id": 5000}
}
```

Map historical fixed bill payments to fixed categories (`rent`, `utilities`,
`insurance`, `debt_payment`) so they do not enter the variable spending target
and get counted again as scheduled bills. Mark identified internal transfers
`transfer` to exclude them. Missing schedules mean missing future inflows or
obligations, with an explicit warning; they are never fabricated.

## Forecast behavior and UI scope

Overview, My Finances, Forecasts, Guardian and Health Score consume live responses.
The dashboard includes account balances, assets less liabilities, trailing
30-day inflows/spending, category totals, next-14-day bills and 30-day alerts.
Forecast controls request `/api/forecast?days=7|30|90`, render every daily point,
show the minimum and ending checking balance, and flag a below-buffer projection.
The table exposes daily values. Request failures produce errors and retry
controls; horizon changes cancel obsolete requests. Other frontend sections
remain explicitly labeled design previews.

LightGBM artifacts are reused when available and the input passes existing
support checks. More frequent spending than the sparse PNC training histories
selects a warned moving-average fallback. The seeded Nessie profile triggers
this check: do not describe its forecasts as LightGBM predictions. Training was
not changed or rerun for this integration. Income/bill arithmetic uses existing
Decimal schedule calculations. Bounds are uncalibrated stress envelopes, not
guaranteed prediction intervals. The historical engineering audit remains
applicable; this work does not establish model accuracy on banking data.

## Verification

```powershell
powershell -ExecutionPolicy Bypass -File scripts/check.ps1
.venv/Scripts/python.exe -m pytest -q
cd frontend
npm.cmd run typecheck
npm.cmd run build
# Start both servers first; Edge must be installed.
npm.cmd run test:e2e
```

Nessie unit tests use mocked HTTP and independently checked signed amounts,
net worth, ownership rejection, invalid money, schedules and horizon lengths.
Browser tests compare the actual API and UI, exercise horizons, and inject
error/shortfall responses. Live sandbox checks must be reported separately.

Executed in this workspace on November 7, 2026: 160 Python tests passed and one
live-PostgreSQL test was skipped; all three Edge browser tests passed. TypeScript
checking and the Vite production build passed. Desktop/mobile screenshots were
captured locally, with no horizontal overflow at 390px width. The live Nessie
customer import, dashboard, context endpoint and 7/30/90-day forecasts returned
HTTP 200 through the frontend proxy. These are functional integration checks,
not validation of forecast accuracy. No live LLM request was needed.
