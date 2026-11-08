# Copilot latency optimization

Measured on 2026-11-08 using the configured `gemini-3.1-flash-lite`, a fixed
synthetic profile dated 2026-11-08, and three sequential samples per question.
Raw samples: [before](copilot-latency-before.json), [after](copilot-latency-after.json).

| Question | Before successful-response median | Before success | After median | After range | After success |
|---|---:|---:|---:|---:|---:|
| Health score | 9.01s | 1/3 | 1.72s | 0.96–2.54s | 3/3 |
| Guardian risk | 2.96s | 3/3 | 0.92s | 0.92–1.04s | 3/3 |
| Spending-cut simulation | No successful reply | 0/3 | 0.94s | 0.93–1.00s | 3/3 |

Failed before-optimization health attempts took 19.95s and 22.78s. Simulation
attempts failed after 11.50–20.02s. These failures are **not** counted as successful
responses in the table. Results demonstrate the target in this session, not an SLA:
provider load, network conditions, cold starts and database retrieval can vary.
This benchmark times the Copilot function, including SDK construction and local
formatting, but excludes HTTP/browser and initial profile/repository loading.

## Bottlenecks and changes

- Previously health/simulation used three Gemini calls, and risk used two. An
  extra "ready" response and a separate structured composition request added
  network latency without contributing any trusted calculations.
- Before the change, composition alone took 6.60s for the successful health sample
  and a median 1.60s for risk. One failed simulation spent 17.14s in composition.
- All successful after samples used **one** Gemini call and zero composition calls.
  After median model time was 1.01s health, 0.62s risk and 0.61s simulation.
- Financial tools were not the bottleneck: after median execution time was about
  2.2ms health, 1.5ms risk and 3.9ms simulation. Local rendering was about 0.1ms.
- Successful calculation results are reused inside the request, using validated
  tool names/arguments. The initial Guardian result is reused when Gemini asks for
  it again. Repeated health component views share one health calculation.
- Tool-selection output is limited to 512 tokens instead of 2,048. Replies use
  concise server-rendered evidence, capped at five statements. After response
  sizes were 409 characters health, 557 risk and 601 simulation in these samples.

## Preserved behavior

The model still interprets the full conversation and resolves scenario follow-ups.
All five tools, financial engines, HTTP schemas, synthetic/prototype labels and
sanitized baseline fallback remain. Tool validation, attempt/round budgets and
provider deadlines still apply. Extra rounds are allowed for argument correction;
those exceptional paths can exceed the 2–4 second target. There is no global cache,
cross-user evidence reuse, or reuse of prior assistant messages as verified facts.

## Reproduce

From `backend`, with Gemini configured:

```powershell
.\.venv\Scripts\python.exe -m scripts.benchmark_copilot --repeats 3 --output ../docs/copilot-latency-run.json
.\.venv\Scripts\python.exe -m pytest -q tests/test_copilot_latency.py tests/test_copilot_intelligence.py
```

The benchmark makes real billable provider requests with synthetic data. It saves
only timings, counts, success categories and the model ID—never keys or reply text.
Latency regression tests simulate network time and count calls, so they do not
depend on machine speed, internet availability or provider credentials. They cover
single-round common questions, repeated calls, changed scenario arguments, focused
health explanations, fresh evidence between requests, and bounded invalid-call repairs.
