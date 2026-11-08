# Score setup and Copilot delivery

## Why the score is blank

`0 / 4 components supported` means the v2 assessment has no confirmed inputs. It
does not mean the score is zero. OpenAI is not involved in financial scoring.

Choose **Confirm inputs to calculate** beside the score ring. Enter take-home
income, essential spending, optional spending, required debt payments and accessible
savings; confirm bill/debt completeness, then calculate. Imported savings are an
upper bound, not an automatically confirmed accessible reserve. Required debt above
the dated schedule leaves payment readiness/reserves incomplete; supply missing
payment dates rather than reducing real obligations to force a score.

Confirmed facts now live in a shared in-memory workspace, so returning from
Overview to Health Score recalculates with those facts instead of resetting to an
empty request. Floating chat also receives them. Editing facts clears the confirmed
version until recalculation; a customer-scope change clears the workspace and chat.
Browser reload closes this in-memory session; no financial inputs are silently
stored on disk or in a database. Score definitions and missing-data safeguards are
unchanged.

## Actual OpenAI diagnostic, 2026-11-08

`python -m scripts.check_openai --generate` was executed against the local private
configuration. Model metadata access for `gpt-4.1-mini` succeeded. One minimal text
generation request failed with a credit/quota error. This establishes a generation
billing/quota problem, not the monetary balance in the account. No customer financial
data was sent by the diagnostic and no key or raw provider exception was printed.

The effective provider was later switched to Gemini after the private key was
updated. Keep one provider setting:

```dotenv
COPILOT_PROVIDER=gemini
GEMINI_MODEL=gemini-3.8-flash
GEMINI_API_KEY=your_private_key
```

Review [API billing](https://platform.openai.com/settings/organization/billing/overview).
OpenAI documents billing/quota errors separately from temporary rate limits in its
[error guide](https://developers.openai.com/api/docs/guides/error-codes). Model listing
success alone does not prove that text generation has available credits.

## Floating chat

**Ask FinPilot** is fixed at the bottom right on desktop and mobile. It supports
conversation, confirmed financial inputs, Escape/close, pending/error states and
customer-scope isolation. API keys remain server-side. No bank transaction tool is
introduced.

Brief social prompts such as “How are you?” may receive a natural live reply without
calling a financial tool. Financial questions still require verified tool evidence;
an unsupported balance, score or recommendation is rejected and replaced with the
deterministic local response.

`ChatResult.delivery` explicitly distinguishes `live`, `offline` and `fallback`, with
provider/model, sanitized reason code and an explanation. Credit exhaustion,
authentication failure, unavailable models and provider outages are visible rather
than hidden behind a local reply. Numeric-grounding and tool-round fallbacks are
also identified. The existing Copilot page displays the same delivery information.

Tests cover sanitized 429/401/404 responses using a mock HTTP transport, explicit
offline delivery, floating chat, billing fallback notices, navigation persistence
and narrow-screen rendering. On 2026-11-08, Gemini model metadata access and a minimal
text-generation request both succeeded without sending financial data. An earlier
attempt returned HTTP 504, so transient provider failures remain possible and fall
back to the local deterministic tools.

Latest executed full Python suite: **219 tests passed, 1 skipped**. The earlier UI
verification also ran **all 15 browser tests successfully** against
the offline fictional banking fixture. Required intelligence checks: **70 passed**
(overlap the full Python suite). TypeScript checking, production build and whitespace
checks passed. An initial browser run caught an Escape handler that depended on
focus remaining in the chat; a document-level handler now closes it correctly.
Initial profile discovery no longer remounts the entire financial workspace.
