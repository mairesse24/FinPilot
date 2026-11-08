# FinPilot

### Understand the risk. Explore your options. Plan with confidence.

**A financial resilience navigator built for HackUTD 2026's PNC Bank Challenge.**

FinPilot brings financial visibility and forward-looking planning into one workspace. Users can review balances, spending, upcoming bills, and financial health, identify potential cash-flow risks, and test spending decisions before acting.

**Detect with Guardian → Simulate with Digital Twin → Understand with AI Copilot**

> Hackathon prototype using synthetic financial data. Forecasts are estimates, scenarios are previews, and no money is moved.

**Demo video:** [Add demo video link]

**Live application:** [Add deployment link]

## The PNC challenge

Built in response to the **PNC 360° Financial Health Navigator** challenge, FinPilot explores how financial tools can help people prepare for what comes next.

A positive account balance today can hide a cash-flow problem tomorrow. Bills, debt payments, and everyday expenses compete for the same funds, while account summaries leave users to connect the dots themselves. FinPilot connects those signals with explanations and what-if planning to answer three practical questions:

- **What needs my attention?**
- **How could a spending adjustment change my outlook?**
- **Why does that change matter?**

## Features

| Feature | Current functionality |
| --- | --- |
| **Financial dashboard** | Synthetic account balances, assets, liabilities, net worth, recent income and spending, category summaries, and upcoming bills. |
| **Explainable health score** | A 0–100 score with five weighted components, supporting explanations, strengths, and areas for improvement. |
| **Cash-flow forecasts** | 7-, 30-, and 90-day projected checking balances, estimated ranges, safety-buffer comparisons, and the projected lowest balance. |
| **Guardian** | Explainable alerts for low projected checking balances, high debt-payment burden, and insufficient emergency reserves, with suggested actions. |
| **Digital Twin** | A discretionary spending-cut sandbox comparing baseline and scenario projections. The API also returns health-score changes and recalculated alerts. |
| **AI Copilot** | Gemini-assisted question interpretation and approved tool selection, with financial answers assembled from backend evidence. Deterministic guidance provides a fallback when Gemini is unavailable. |
| **Economic Lab** | An illustrative cost-increase calculator using the current monthly spending snapshot. |
| **FinPilot Wrapped** | A navigable recap of spending, financial health, forecasts, risks, and suggested next steps derived from the loaded backend snapshot. |

### Financial health, explained

| Component | Baseline weight |
| --- | ---: |
| Cash flow | 25% |
| Emergency fund | 25% |
| Debt burden | 20% |
| Spending discipline | 15% |
| Bill readiness | 15% |

These transparent prototype rules produce a financial health indicator, not a credit score or a validated financial assessment.

## How FinPilot works

1. **Understand the snapshot.** Review balances, spending, financial health, upcoming obligations, and cash-flow forecasts.
2. **Detect a potential problem.** Guardian evaluates the profile and projected cash flow, explaining each alert with supporting figures and an action to explore.
3. **Test a response.** Digital Twin sends a spending-cut scenario to the backend, which recalculates the outlook and compares it with the baseline.
4. **Explain the result.** Copilot can retrieve account summaries, health scores, forecasts, Guardian alerts, and simulation results through validated, read-only tools.
5. **Review the tradeoffs.** Compare the estimated improvement with remaining risks. Scenarios do not update accounts or persist a financial plan.

### Try the demo story

- Open **Overview** and inspect the financial health breakdown.
- Visit **My Finances**, then explore the spending recap in **FinPilot Wrapped**.
- Open **Guardian** to review the projected cash-flow risk.
- Launch **Digital Twin** and compare a spending cut with the current path.
- Ask **AI Co-Pilot**: “Explain my biggest financial risk.”
- Follow up: “What if I cut $200 over 10 days?”

A spending cut is the **total reduction over the specified period**, rather than a recurring monthly amount. Demo figures depend on the configured data date and repository. Describe the scenario in chat: the separate simulation drawer does not automatically pass its selection to Copilot.

## Tech stack and architecture

| Layer | Technologies |
| --- | --- |
| Frontend | React 19, TypeScript, Vite 8 |
| Styling and icons | Tailwind CSS 4, custom CSS, Lucide React |
| Backend | Python, FastAPI, Uvicorn |
| Validation and configuration | Pydantic, Pydantic Settings |
| Data | Built-in synthetic repository; optional PostgreSQL/Supabase via Psycopg |
| AI | Google Gen AI Python SDK and a configurable Gemini model |
| Verification tooling | Pytest, Node.js test runner, TypeScript checks, frontend build, and API integration scripts |
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

The baseline forecast combines weekday spending averages from the trailing 90 days with scheduled income and bills. Its approximate uncertainty range widens over the forecast horizon. Financial calculations use Python and Decimal-based monetary logic; the language model selects tools rather than supplying financial figures.

The intelligence gateway supports separate implementations and falls back to baseline behavior when modules are absent or fail. In the current backend checkout, scoring, forecasting, Guardian, and simulation have built-in baseline implementations; Gemini supplies the optional Copilot path.

### Current repository structure

```text
FinPilot/
├── README.md
├── frontend/
│   ├── src/                  # UI, API client, financial snapshot, Wrapped
│   ├── scripts/              # Client tests and backend integration check
│   ├── .env.example
│   └── BACKEND.md
├── FinPilot-Copilot/          # Separate, nested backend Git checkout
│   ├── backend/
│   │   ├── app/
│   │   │   ├── routes/       # HTTP endpoints
│   │   │   ├── services/     # Feature orchestration and intelligence gateway
│   │   │   ├── schemas/      # Request and response models
│   │   │   ├── calc/         # Financial calculations
│   │   │   ├── baseline/     # Deterministic feature implementations
│   │   │   ├── db/           # In-memory and PostgreSQL repositories
│   │   │   └── tools/        # Copilot's read-only calculation tools
│   │   ├── intelligence/     # Gemini Copilot and evidence rendering
│   │   ├── scripts/          # Database seed and benchmark utilities
│   │   └── tests/
│   ├── docs/
│   └── render.yaml
└── demo/finpilot/             # Recording plan and subtitles
```

> **Development snapshot:** application work is distributed across feature branches and local integration files. The current local `main` snapshot does not contain the assembled app. `FinPilot-Copilot/` is a separate Git checkout, not a configured submodule. The setup below applies to this assembled workspace; cloning `main` alone will not reproduce it.

## Local installation and setup

### Prerequisites

- Node.js compatible with the project's Vite 8 release and npm
- Python 3.11+ recommended; the backend deployment configuration specifies Python 3.12
- The frontend and backend directories shown above
- Optional: a PostgreSQL/Supabase database and a Gemini API key

### 1. Start the backend

From the workspace root, in PowerShell:

```powershell
cd FinPilot-Copilot/backend
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

On macOS/Linux:

```bash
cd FinPilot-Copilot/backend
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

No database connection is required for the built-in synthetic demo. Without a Gemini key, Copilot uses baseline guidance.

To customize configuration, create a local backend `.env` from `.env.example` **only if `.env` does not already exist**. Preserve existing settings. Restart the API after changing its environment configuration.

- Interactive API documentation: **http://127.0.0.1:8000/docs**
- Service health check: **http://127.0.0.1:8000/healthz**

### 2. Start the frontend

In a second terminal, from the workspace root:

```bash
cd frontend
npm install
npm run dev
```

Open the URL printed by Vite, normally **http://localhost:5173**. The development server proxies `/api` requests to the backend on port 8000.

For local overrides, create `frontend/.env.local` using the frontend example as a guide, preserving any existing file. Restart Vite after configuration changes.

### 3. Optional integrations

- **Gemini:** configure the provider key on the backend and select automatic intelligence mode. Responses expose source metadata so model-backed results can be distinguished from fallback guidance.
- **PostgreSQL/Supabase:** configure the database connection and follow the [database setup guide](FinPilot-Copilot/docs/supabase-setup.md). Review the target before running database seed commands; reset options can remove data.
- **Repeatable demos:** pin the backend reference date to keep forecasts and explanations consistent.
- **Separate frontend hosting:** configure the frontend API origin before building and allow the frontend origin in backend CORS settings. Vite's development proxy is not included in production builds.

## Environment variables

Variable **names only** are listed here. Consult the example files for configuration guidance.

| Scope | Names |
| --- | --- |
| Frontend | `API_PROXY_TARGET`, `VITE_API_BASE_URL` |
| Backend data and runtime | `DATABASE_URL`, `CORS_ORIGINS`, `DEMO_USER_ID`, `INTELLIGENCE_MODE`, `AS_OF_DATE` |
| Backend Copilot | `GEMINI_API_KEY`, `GEMINI_MODEL`, `COPILOT_TIMEOUT_SECONDS`, `COPILOT_MAX_ROUNDS`, `COPILOT_MAX_TOOL_CALLS` |
| Frontend integration check | `FINPILOT_FRONTEND_URL` |
| Future integration placeholder | `FRED_API_KEY` — present in the backend example but unused by the current app |

Keep provider keys and database credentials on the backend. Frontend `VITE_*` configuration is exposed to the browser. Never commit populated environment files.

## API overview

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/healthz` | Service and repository connectivity check |
| GET | `/api/dashboard` | Financial overview |
| GET | `/api/accounts` | Account information |
| GET | `/api/transactions` | Transaction history |
| GET | `/api/health` | Health score and explanations |
| GET | `/api/forecast` | Cash-flow projection; accepts a 7-, 30-, or 90-day horizon |
| GET | `/api/guardian` | Risk alerts and suggested actions |
| POST | `/api/simulate` | Spending-cut comparison |
| POST | `/api/chat` | Copilot conversation |

See FastAPI's `/docs` page and the [API contracts](FinPilot-Copilot/docs/api-contracts.md) for request and response schemas.

## Development checks

Frontend, from `frontend/`:

```bash
npm run test:client
npx tsc --noEmit
npm run build
```

Backend, from `FinPilot-Copilot/backend/`, in PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pytest -q --ignore=tests/db
```

On macOS/Linux, use `.venv/bin/python` instead. With both development servers running, execute from `frontend/`:

```bash
npm run check:backend
```

Database integration tests require a dedicated configured database. Copilot tests use mocked provider responses; passing them does not establish live Gemini availability or answer quality.

## Prototype scope and ongoing work

- All financial data in the current assembled workspace is synthetic.
- Forecasts and scoring thresholds are prototype assumptions, not guaranteed outcomes or professional financial advice.
- Economic Lab performs a local sensitivity calculation; it does not fetch live economic indicators.
- Wrapped uses the loaded snapshot and has no dedicated backend endpoint.
- Spending-cut scenarios preview outcomes without changing accounts or saving plans.
- Copilot history lasts for the lifetime of the open chat drawer.
- The demo user selector is not production authentication or authorization.
- The locally available `gokul` branch snapshot contains additional LightGBM forecasting, economic analysis, and Nessie sandbox work. These are separate branch implementations, not claimed here as integrated features of the current workspace.

## Team

FinPilot was collaboratively developed by a three-member team for HackUTD 2026. While each member focused on particular areas, development involved collaboration across the frontend, backend, and financial intelligence components.

| Team Member | Contributions |
| --- | --- |
| **Mairesse** | Frontend development, UI/UX design, application integration, and backend development. |
| **Gokul** | AI/ML development, language model integration, financial intelligence, and backend development. |
| **Abhishek** | Backend development, frontend development, and application integration. |

Our team collaborated to bring together FinPilot's financial dashboard, risk detection, financial simulations, and AI-powered guidance into a unified application.

## Built at HackUTD 2026

FinPilot was built for **HackUTD 2026** in response to the **PNC Bank Challenge**.

Thank you to HackUTD's organizers, mentors, volunteers, and PNC challenge sponsors for creating the opportunity to explore more understandable, proactive financial tools.
