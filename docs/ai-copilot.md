# Feature 6: Gemini Financial Copilot

## Setup (Windows PowerShell)

From the repository root:

```powershell
cd backend
# Only if .venv does not already exist (Python 3.11+ recommended):
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
# Only if .env does not already exist; preserve existing database/settings values:
Copy-Item .env.example .env
```

Edit `backend/.env` locally:

```dotenv
GEMINI_API_KEY=your-key-from-google-ai-studio
GEMINI_MODEL=gemini-3.1-flash-lite
INTELLIGENCE_MODE=auto
AS_OF_DATE=2026-11-07
COPILOT_TIMEOUT_SECONDS=20
COPILOT_MAX_ROUNDS=4
COPILOT_MAX_TOOL_CALLS=8
```

`GEMINI_API_KEY` is required for Gemini. The model is configurable; the default is
the stable Gemini 3.1 Flash-Lite model with function calling and structured outputs.
The key must have access/quota for that model. SDK version `google-genai==2.34.0`
is pinned to the version used by the tests. Set keys on the backend only; never
use a `VITE_*` variable or commit `.env`. The Copilot does not use OpenAI or FRED.
`DATABASE_URL` is optional: leaving it empty uses the built-in synthetic customer.
For a predictable demo, pin `AS_OF_DATE` as above.

Start the API from `backend`:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Restart after changing environment variables; settings are cached. On Linux/macOS,
use `python3 -m venv .venv` and `.venv/bin/python` in place of the Windows commands.
For Render, add `GEMINI_API_KEY` as a secret and `GEMINI_MODEL` to service environment
settings, then redeploy. No new endpoint or database table is required.

## How it works

The existing `/api/chat` route loads the user profile and passes its request-scoped
settings to `ToolRegistry`. `Gateway` discovers synchronous
`intelligence.copilot.chat(messages, tools) -> ChatResult` in auto mode.

The Copilot starts with verified Guardian context, preserving a tool-call record
for that fetch. It sends the complete bounded request history to Gemini, mapping
assistant messages to Gemini's `model` role. Previous assistant answers remain
untrusted context; calculations are rerun using the current profile.

All five registry tools are declared using the SDK's function declarations.
Automatic function execution is disabled. The server validates tool names, numeric
types, finite positive spending amounts (up to 100,000), allowed forecast horizons,
scenario horizons (1–90), and rejects unexpected fields before dispatch. Tool
errors can be corrected within the call budget. The full Gemini function-call
content, signatures, parallel calls and call IDs are preserved when returning results.

The common path uses one Gemini function-selection request. The model interprets
conversation history and chooses approved tools/arguments; the server executes them
and immediately renders a concise selection of verified statements. It does not
request another model turn just to say it is ready, or to compose an evidence-ID
plan. Further rounds are reserved for correcting invalid arguments. Automatic tool
execution remains disabled; thought signatures and call IDs are preserved on repairs.

Successful results are cached only inside one chat invocation, keyed by tool name
and validated calculation arguments. Duplicate requests reuse those results without
re-running financial engines or duplicating tool records. Errors are not cached;
separate requests, users, dates and scenario arguments never share evidence. A health
component selector is presentation metadata; it is validated and removed before
calling the existing health calculation, so focused explanations use the same cache.

Answers contain at most five verified statements: risk prioritizes Guardian's first
severity-ordered alert; health normally shows the score and weakest/strongest factors
(or an explicitly selected component); forecasts and simulations keep the before/after
figures and uncertainty/remaining-risk context. The output is formatted into bullets
with bold financial numbers and separate risk/action sections. All financial text
comes from backend evidence, not model prose. Every answer labels synthetic prototype
estimates and disclaims guaranteed outcomes. Plain model text or JSON is never used
as financial evidence, and the public reply remains a string.

React supports only a small Markdown subset (headings, bullets, paragraphs, bold)
using safe React elements and text nodes. It never uses raw HTML, executable links,
image embeds or dangerouslySetInnerHTML. Older/baseline replies receive spacing too.

The public request/response stays unchanged: `messages` in, `reply`, `tool_calls`,
`meta` out. The route stamps source, date and warning metadata. New health explanation,
forecast uncertainty and simulation fields are additive *internal tool results*,
not changes to the HTTP schema.

Public fallback warnings use a friendly backup-estimate notice. Internal module names
and exception messages are not sent to users. Server diagnostics retain only module
and exception type. The React client also replaces raw warnings and transport errors
with safe messages, including when talking to an older backend.

Guardian uses a 30-day risk outlook; tools and evidence label their data date and
horizon. React refreshes its financial snapshot on chat opening/completion, window
focus, and every minute. It rejects mixed-date snapshots instead of combining
yesterday's Guardian data with today's Copilot calculations. Without `AS_OF_DATE`,
the backend rolls its data date forward daily, so historical replies can legitimately
differ from a newly refreshed forecast. Pin the date for a repeatable demo.

Default limits are four provider rounds (maximum; normally one), eight tool
executions (including proactive Guardian and invalid attempts), and a 20-second
generation budget. Each SDK request uses the remaining budget in milliseconds with
one HTTP attempt. Deadline checks stop further work and reject late responses;
SDK transport timeouts bound network waits. These are cooperative deadlines, not
process-level interruption of a slow teammate's synchronous tool implementation.

No key, provider error, invalid output, tool failure, or exceeded budget raises a
sanitized exception into the existing gateway. It returns baseline guidance with
`meta.source="baseline"` and `meta.warning`. Raw provider exception messages, keys
and URLs are not forwarded. `INTELLIGENCE_MODE=baseline` bypasses Gemini entirely.

## Test through Swagger

Open http://127.0.0.1:8000/docs, expand `POST /api/chat`, and use **Try it out**:

```json
{"messages":[{"role":"user","content":"Explain my biggest financial risk and what I could explore."}]}
```

Then try:

```json
{"messages":[{"role":"user","content":"How was my health score calculated?"}]}
```

For a simulation, ask `What if I cut $200 over 10 days?`. For the follow-up, resend
the original user message, the actual previous assistant `reply`, and a new user
message: `What if I cut $250 instead?`. The backend is stateless; it cannot remember
messages that the client does not send. Inspect `tool_calls` for `run_simulation`
with amount 250 and horizon 10. Compare figures against `/api/simulate` for the same
user, amount and horizon. A cut is a *total over the specified horizon*, not a
recurring monthly amount. Full future conversation reasoning requires a live-model
check; mocked tests verify history transport and recomputation, not model accuracy.

Check `meta.source`: `model` means the Gemini module completed; `baseline` means
fallback or forced baseline mode. No live Gemini test is performed by pytest.

## Test through the existing React frontend

Keep the API running on port 8000. In the outer `FinPilot/frontend` directory:

```powershell
npm run dev
```

Open the printed URL (normally http://localhost:5173), choose **AI Co-Pilot**, then
**Open conversation** (or use the Overview shortcut). Ask the same risk, score and
simulation questions. Keep the drawer open while asking follow-ups: the current
frontend stores history only for that drawer's lifetime. Its existing Vite proxy
forwards `/api` to port 8000; no frontend changes are required. In browser Network
tools, inspect `/api/chat` to see `meta.source`, warnings and tool calls (the current
UI does not render tool-call traces). Direct cross-origin deployments still need
the backend `CORS_ORIGINS` to include the frontend origin.

## Automated checks

From `backend`:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_copilot_intelligence.py tests/test_chat_route.py tests/test_tools.py tests/test_gateway.py tests/test_e2e_demo_flow.py
.\.venv\Scripts\python.exe -m pytest -q --ignore=tests/db
```

Provider-mocked tests use real SDK types and the real in-memory calculation tools.
They cover history/follow-up transport, parallel calls, health evidence, forecasts,
simulation relationships, invalid arguments, injection/fabricated output, call and
time budgets, missing credentials, sanitized failures, and route/gateway metadata. Deterministic
latency tests assert one model round for common questions and request-local evidence reuse.
Database tests are excluded from the broader command because they can reset a database.

## Remaining boundaries

- No changes to React, financial engines, HTTP schemas, authentication or persistence.
- The existing frontend does not pass a selected Guardian alert or Digital Twin
  scenario into chat; describe it in a message or rerun it conversationally.
- Tool result metadata does not currently preserve all downstream module warnings.
- Existing teammate integrations use `intelligence.forecast` and `intelligence.simulate`
  in service code, despite older docs naming `forecasting.py` and `simulator.py`.
  Coordinate those module names before teammates merge their implementations.

Official references: [Google Gen AI Python SDK](https://googleapis.github.io/python-genai/)
and [Gemini 3.1 Flash-Lite](https://aistudio.google.com/docs/models/gemini-3.1-flash-lite).
