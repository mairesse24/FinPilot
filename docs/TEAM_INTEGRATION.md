# FinPilot team integration handoff

This branch contains Member 3's intelligence prototype. The shared repository is currently hosted under the historical `ForeCastle` GitHub name; the application name is FinPilot.

## Folder ownership

Use the team blueprint's layout. This branch does not create placeholder app/frontend implementations that could conflict with teammates' work.

```text
FinPilot/
  frontend/                  Member 1: Next.js and UI (to be added)
  backend/
    __init__.py              Python namespace marker
    app/                     Member 2: FastAPI, routes, schemas, DB (to be added)
    intelligence/            Member 3: calculations, forecasting, copilot
  scripts/                   Named local setup, demo and validation commands
  tests/                     Member 3 tests; add distinct backend/UI tests
  data/synthetic/            Fictional examples and editable stress cases
  data/economy/              Cache provenance; raw cache is downloaded locally
  artifacts/reports/         Evaluation and stress reports
  artifacts/models/          Local generated model artifacts; ignored by Git
  docs/                      Contracts, architecture, audit and handoff
  requirements-ml.txt         Member 3 core dependencies
  requirements-copilot.txt    Optional provider dependencies plus ML
```

Member 2 should own the application's `backend/app/`, server entry point, database, authentication, REST schemas and deployment configuration. Member 1 should own `frontend/`. Member 3 owns `backend/intelligence/`. Shared README, dependency and contract changes should be coordinated through pull requests. Do not rename or move another member's folders merely to merge this branch.

## Run Python from the repository root

Use imports such as:

```python
from backend.intelligence.service import analyze, analyze_horizons
from backend.intelligence.simulator import simulate
from backend.intelligence.copilot import chat
```

The backend launch must make the repository root importable. For example, **after Member 2 adds the server**, a root-level launch may be `python -m uvicorn backend.app.main:app`. That server does not exist on this branch. Avoid changing the working directory to `backend/` and then assuming `backend.intelligence` remains importable. Do not copy intelligence functions into `backend/app/services/`; call the existing functions instead.

## Dependencies

For all current tests and optional chatbot adapters:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements-copilot.txt
.venv/Scripts/python.exe -m pytest tests -q
```

`requirements-ml.txt` supports core calculations/inference without chatbot credentials. The current test suite also imports some provider dependencies unconditionally, so use the copilot requirements for the full test run until that audit finding is fixed. Prefer Python 3.12+ for compatibility with the pinned ML lock; the current development environment is Python 3.14. A clean-install Python-version matrix has not been verified.

Member 2 can keep an application requirements file instead of replacing these files. A future `backend/requirements.txt` may include `-r ../requirements-copilot.txt`, followed by the backend's own FastAPI, database and deployment dependencies. This inclusion is relative to the requirements file. Never overwrite a teammate's requirements wholesale.

## Data and API contract

The callable boundary and proposed routes are documented in `docs/api-contracts.md`. There are no first-party HTTP routes in this branch.

- Derive customer identity from authentication; do not trust an ID sent by the LLM or browser.
- Convert database records into the documented normalized customer and one-customer contiguous daily history, with explicit zero days and matching `as_of`.
- Keep scheduled bills separate from forecast variable spending. Agree on a single card-consumption/payment accounting convention before real-user use; the current approximation has audit findings.
- Pass the same customer, forecast and analysis snapshot to simulation and copilot. Current lineage checks are incomplete, so caller-side scoping alone is not a complete production safeguard.
- Dates are ISO calendar dates. Scenario percentages are fractions; indicator rates are percentage points. Monetary amounts are USD, with current floating-point limitations documented in the audit.
- Use `analyze_horizons` to obtain consistent 7/30/90-day results. Render warnings, actual serving model, forecast assumptions and missing exposure fields.
- Guardian creates alert candidates, not delivered notifications. Member 2 owns persistence, deduplication and delivery; Member 1 owns alert cards and simulation controls.
- Economic snapshots must align with financial dates. Observation timestamps are not release timestamps; current-vintage research is not a valid historical-availability guarantee.

Frontend mock responses can use `data/synthetic/demo.json` and `conditions-demo.json`. They are fictional illustrations; generated JSON is not an executable schema or proof of financial correctness. Coordinate Pydantic/TypeScript schemas before relying on field names across branches.

## Models and local data after checkout

The vendor checkout, virtual environment, raw economic history and trained model files are intentionally not pushed. On a fresh checkout:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/bootstrap-pnc.ps1
.venv/Scripts/python.exe -m backend.intelligence.training
.venv/Scripts/python.exe -m scripts.fetch_economy
.venv/Scripts/python.exe -m scripts.stress_test
```

The fetch step requires network access. Model training and CSV stress tests need no LLM credits. Inference falls back to a labeled rolling average when model metadata is absent; that fallback is not equivalent to loading the trained model. Deployment must provision model artifacts explicitly. Checksummed artifact publication remains an audit remediation item.

Each developer creates their own ignored `.env` from `.env.example`. Do not commit real provider keys, service-role keys, private banking data or `.venv`. The copilot CLI loads root `.env`; Member 2's application must load configuration itself. Do not prefix secret backend variables with frontend public-variable prefixes.

## Branch and merge practice

This work is pushed to `gokul`; it does not merge into or overwrite `main`. Teammates should review the branch or merge through a pull request. Before integration, fetch the latest remote state and agree ownership of any overlapping files. Keep commits focused and resolve conflicts by preserving both members' required behavior, not by choosing an entire side without inspecting it. The remote branches inspected during this handoff contained only a README; teammates' unpublished structures could not be compared.

## Current readiness

Read `docs/ENGINEERING_AUDIT.md` before treating outputs as production-grade. At audit time, 39 existing tests and 52 declared stress cases passed, while additional probes exposed ingestion, financial scoring, date/freshness, card accounting and copilot grounding defects. These have **not** been remediated merely by preparing this branch. Stock-direction research abstains; observed-condition labels are rules. There is no production auth, persistent ledger, net-worth API, notification service or completed FinPilot UI on this branch.
