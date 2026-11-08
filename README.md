# FinPilot

### Understand the risk. Explore your options. Plan with confidence.

**An AI-powered financial intelligence and resilience platform built for the PNC Bank and Capital One challenges at HackUTD 2026.**

FinPilot connects financial visibility with actionable planning. It brings account balances, spending, upcoming bills, and financial health into one workspace—then helps users identify potential risks, test spending adjustments, and understand the results.

**Detect with Guardian → Simulate with Digital Twin → Understand with AI Copilot**

> FinPilot is a hackathon prototype using synthetic financial data. Forecasts are estimates, scenarios are previews, and no money is moved.

**Demo video:** [Add demo video link]

**Live application:** [Add deployment link]

## HackUTD 2026 challenges

FinPilot was developed for both the PNC Bank and Capital One challenges at HackUTD 2026.

- PNC — 360° Financial Health Navigator: Bring financial accounts, obligations, wellness indicators, forecasts, and actionable guidance into one experience.
- Capital One — Nessie API: Explore simulated banking account and transaction data through Capital One’s Nessie banking sandbox. Nessie integration code was found in separate branch work; end-to-end integration in the assembled app has not been verified.

Together, these tracks shaped FinPilot’s approach to turning financial data into forward-looking decisions.

A healthy-looking balance today can hide a cash-flow problem tomorrow. Bills, debt payments, and everyday spending compete for the same funds, while conventional account summaries leave users to connect the dots themselves.

FinPilot helps answer three questions:

- What needs my attention?
- How could a spending adjustment change my outlook?
- Why does that change matter?

## Features

| Feature | What the current prototype does |
| --- | --- |
| Financial dashboard | Displays synthetic account balances, assets, liabilities, net worth, recent income and spending, category breakdowns, and upcoming bills. |
| Explainable health score | Calculates a 0–100 score with five weighted components, supporting explanations, strengths, and areas for improvement. |
| Cash-flow forecasts | Shows 7-, 30-, and 90-day projected checking balances, estimated ranges, a safety buffer, and the projected lowest balance. |
| Guardian | Flags low projected checking balances, high debt-payment burden, and insufficient emergency reserves, with explanations and suggested actions. |
| Digital Twin | Tests a discretionary spending cut and compares baseline and scenario projections. The API also returns health-score changes and recalculated alerts. |
| AI Copilot | Uses Gemini to interpret questions and select approved calculation tools. Financial answers are assembled from backend evidence, with deterministic fallback guidance when Gemini is unavailable. |
| Economic Lab | Lets users apply an illustrative percentage increase to current monthly spending and inspect the additional cost. |
| Financial Wrapped | Presents a navigable recap of spending, financial health, forecasts, risks, and suggested next steps derived from the loaded financial snapshot. |

### Financial health, explained

| Component | Weight |
| --- | --- |
| Cash flow | 25% |
| Emergency fund | 25% |
| Debt burden | 20% |
| Spending discipline | 15% |
| Bill readiness | 15% |

These are transparent prototype scoring rules, not a credit score or a validated financial assessment.

## How FinPilot works

1. Understand the snapshot. The dashboard loads account information, spending categories, financial health, risk alerts, and cash-flow forecasts.
2. Detect a potential problem. Guardian evaluates the profile and projected cash flow. An alert explains the risk, supporting figures, and an action to explore.
3. Test a response. Digital Twin sends a spending-cut scenario to the backend, which compares the adjusted outlook against the baseline.
4. Explain the result. Copilot can retrieve account summaries, health scores, forecasts, Guardian alerts, and simulation results through approved tools.
5. Review the tradeoffs. Users can compare the estimated improvement with remaining risks. Scenarios do not update accounts or persist a financial plan.

### Suggested demo flow

- Open the financial overview and inspect the health-score breakdown.
- Visit Guardian and select a suggested spending scenario.
- Adjust the spending cut in Digital Twin and compare projected balances.
- Ask Copilot: “Explain my biggest financial risk.”
- Follow up with: “What if I cut $200 over 10 days?”

A spending cut represents the total reduction over the specified period, rather than a recurring monthly amount. Exact demo figures depend on the configured data date and repository.

## Tech stack and architecture

| Layer | Technologies |
| --- | --- |
| Frontend | React 19, TypeScript, Vite 8 |
| Styling and icons | Tailwind CSS 4, custom CSS, Lucide React |
| Backend | Python, FastAPI, Uvicorn |
| Validation and configuration | Pydantic, Pydantic Settings |
| Data | Built-in synthetic repository; optional PostgreSQL/Supabase via Psycopg |
| Banking sandbox (separate branch) | Capital One Nessie API integration work; not verified in the assembled app |
| Additional intelligence (separate branch) | LightGBM forecasting and economic analysis work |
| AI | Google Gen AI Python SDK and configurable Gemini model |
| Verification | Pytest, Node.js test runner, TypeScript checks, frontend build and API integration scripts |
| Deployment configuration | Render backend Blueprint |

```text
React + TypeScript frontend
          |
          | JSON over HTTP
          | Vite /api proxy during development
          v
FastAPI routes + Pydantic schemas
          |
       Services
          |
          +-- Repository
          |     +-- In-memory synthetic data
          |     +-- PostgreSQL / Supabase
          |
          +-- Deterministic financial calculations
          |
          +-- Intelligence gateway
                  +-- Available intelligence modules
                  +-- Built-in baseline implementations

Copilot -> validated read-only tools -> financial services
```

The baseline forecast uses weekday spending averages from the trailing 90 days, combined with scheduled income and bills. Its estimated range widens over the forecast horizon.

The intelligence gateway supports separate implementations while retaining baseline behavior when modules are absent or fail. In the inspected checkout, financial scoring, forecasting, Guardian, and simulation have built-in baseline implementations; Gemini powers the optional Copilot path.

### Current workspace layout

```text
FinPilot/
├── README.md
├── frontend/
│   ├── src/                  # UI, API client, snapshot and recap logic
│   ├── scripts/              # Client tests and backend connection check
│   └── BACKEND.md
├── FinPilot-Copilot/          # Separate backend Git checkout
│   ├── backend/
│   │   ├── app/
│   │   │   ├── routes/
│   │   │   ├── services/
│   │   │   ├── schemas/
│   │   │   ├── calc/
│   │   │   ├── baseline/
│   │   │   ├── db/
│   │   │   └── tools/
│   │   ├── intelligence/
│   │   └── tests/
│   └── docs/
└── demo/finpilot/             # Recording plan and subtitles
```

## Run locally

### Prerequisites

- Node.js compatible with Vite 8; Node.js 22.12+ is a suitable starting point
- Python 3.11+; the backend deployment configuration specifies Python 3.12
- npm
- Optional: PostgreSQL/Supabase and a Gemini API key

Repository status: These instructions describe the assembled development workspace inspected for this README. A checkout of the then-current main branch alone did not include the application. The nested backend is a separate checkout, so application branches must be assembled or merged before these steps apply to a fresh clone.

### 1. Start the backend

From the workspace root, in PowerShell:

```powershell
cd FinPilot-Copilot/backend
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

For macOS/Linux, use python3 to create the virtual environment and .venv/bin/python to run commands.

The backend can run without database credentials or a Gemini key:

- No database configuration uses built-in synthetic data.
- No Gemini key uses baseline Copilot guidance.

Interactive API documentation: http://127.0.0.1:8000/docs
Service health check: http://127.0.0.1:8000/healthz

To customize settings, create a local backend .env from .env.example only if one does not already exist. Preserve existing team settings and keep credentials private.

### 2. Start the frontend

In a second terminal, from the workspace root:

```bash
cd frontend
npm install
npm run dev
```

Open the URL printed by Vite, normally http://localhost:5173.

The development server proxies /api requests to the backend on port 8000. For separately hosted frontend and backend, configure the frontend API origin before building and allow the frontend origin in the backend CORS configuration. The development proxy is not included in a production build.

### 3. Optional integrations

- Gemini: Configure the backend provider key and use automatic intelligence mode.
- PostgreSQL/Supabase: Configure the database connection and follow the backend database setup documentation.
- Repeatable demo: Pin the backend data date so forecasts and explanations use a consistent reference date.

Database seeding can reset data. Review the setup instructions and target database before running seed commands.

## Environment variables

Variable names only are listed below. Use the example environment files for configuration guidance.

### Frontend

```text
API_PROXY_TARGET
VITE_API_BASE_URL
```

### Backend

```text
DATABASE_URL
CORS_ORIGINS
DEMO_USER_ID
INTELLIGENCE_MODE
AS_OF_DATE
GEMINI_API_KEY
GEMINI_MODEL
COPILOT_TIMEOUT_SECONDS
COPILOT_MAX_ROUNDS
COPILOT_MAX_TOOL_CALLS
```

### Integration check

```text
FINPILOT_FRONTEND_URL
```

The backend example also contains FRED_API_KEY as a future integration placeholder. The inspected application does not use it.

Keep provider keys and database credentials on the backend. Frontend VITE_* configuration is exposed to the browser.

## API overview

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | /healthz | Service and repository connectivity check |
| GET | /api/dashboard | Financial overview |
| GET | /api/accounts | Account information |
| GET | /api/transactions | Transaction history |
| GET | /api/health | Financial health score and explanations |
| GET | /api/forecast?days=7\|30\|90 | Cash-flow projection |
| GET | /api/guardian | Risk alerts and suggested actions |
| POST | /api/simulate | Spending-cut comparison |
| POST | /api/chat | Copilot conversation |

See FastAPI's /docs page for request and response schemas.

## Development checks

Frontend:

```bash
cd frontend
npm run test:client
npx tsc --noEmit
npm run build
```

Backend:

```powershell
cd FinPilot-Copilot/backend
.\.venv\Scripts\python.exe -m pytest -q --ignore=tests/db
```

With both development servers running, execute from frontend:

```bash
npm run check:backend
```

Database integration tests require a dedicated configured database. Copilot tests use mocked provider responses; passing them does not establish live Gemini availability or answer quality.

## Banking data and project integrations

FinPilot was designed for both the PNC 360° Financial Health Navigator and Capital One challenges. The project blueprint considered the PNC hackathon starter kit for synthetic financial profiles and calculations, Capital One's Nessie API for simulated banking accounts and transactions, Supabase PostgreSQL for storage, LightGBM for predictive spending, and FRED for economic indicators. These were project design targets, not all verified features of the assembled application.

The locally inspected gokul branch snapshot contains Nessie sandbox integration, LightGBM forecasting, and economic analysis code. Those are real areas of team development, but the available inspection did not establish that they are merged, deployed, or functioning end-to-end with the current frontend. The current assembled workspace uses synthetic financial data and baseline calculations; do not describe it as connected to live bank accounts.

## Prototype scope

- Financial data is synthetic; the inspected workspace does not connect to real bank accounts.
- Forecasts and scoring thresholds are prototype assumptions.
- Economic Lab performs a local spending sensitivity calculation; it does not fetch live economic indicators.
- Wrapped uses the loaded financial snapshot; there is no dedicated Wrapped API.
- Simulations preview spending cuts without changing accounts or saving plans.
- Copilot conversation history lasts for the lifetime of the open chat drawer.
- The demo user selector is not authentication or production authorization.
- Separate feature-branch work includes LightGBM forecasting, economic analysis, and Nessie sandbox integration. Those capabilities were not confirmed as integrated into the inspected workspace.

## Team

FinPilot was collaboratively developed by a three-member team for HackUTD 2026. While each member focused on particular areas, development involved collaboration across the frontend, backend, and financial intelligence components.

| Team member | Contributions |
| --- | --- |
| Mairesse | Frontend development, UI/UX design, application integration, and backend development |
| Gokul | AI/ML development, language model integration, financial intelligence, and backend development |
| Abhishek | Backend development, frontend development, and application integration |

Our team collaborated to bring together FinPilot's financial dashboard, risk detection, financial simulations, and AI-powered guidance into a unified application.

## Built at HackUTD 2026

FinPilot was built for HackUTD 2026, addressing both the PNC Bank and Capital One challenges.

Thank you to HackUTD's organizers, mentors, volunteers, and PNC and Capital One challenge sponsors for creating the opportunity to explore more understandable, proactive financial tools.
