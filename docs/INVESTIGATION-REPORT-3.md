# FinPilot — Frontend Engineering Audit & Remediation Report

> Report #3 (pasted by Abhishek and saved as received). Related: [INVESTIGATION-REPORT.md](INVESTIGATION-REPORT.md) (#1) and [INVESTIGATION-REPORT-2.md](INVESTIGATION-REPORT-2.md) (#2).

**Project:** FinPilot  
**Environment:** Deployed hackathon prototype  
**Frontend:** Netlify  
**Reviewed page:** Overview Dashboard  
**Review date:** November 8, 2026  
**Audience:** Senior Software Engineer / Frontend & Backend Engineering Team

---

## 1. Executive Summary

The FinPilot Overview dashboard has a solid foundation, combining financial health analysis, cash-flow forecasting, account summaries, upcoming bills, and financial risk detection.

However, the current implementation has several issues affecting:

1. Financial data credibility and consistency.
2. Transparency of financial calculations.
3. User-facing presentation and information hierarchy.
4. Explainability of predictive analytics.
5. Clarity and usefulness of financial recommendations.

The primary objective is to make FinPilot feel like a trustworthy financial intelligence product rather than an engineering prototype.

**Important:** This report is based on the deployed Overview page. Suspected issues must be validated against backend calculations and underlying data before changing business logic. Recommendations concerning other application sections are product-level recommendations, not verified defects.

---

# 2. Critical Issues (P0)

These should be addressed before the next judging demonstration.

## P0.1 — Unexplained Cash-Flow Forecast Discontinuity

**Observed behavior**

The projected checking balance changes dramatically between consecutive days:

| Date | Projected checking |
|---|---:|
| Nov 17 | $358.50 |
| Nov 18 | $2,418.02 |

This represents an overnight increase of $2,059.52.

There may be a scheduled income event responsible for this increase, but the dashboard does not explain the source.

**Why this matters**

Users need to understand why their projected balance changes. An unexplained increase or decrease makes the forecasting engine appear unreliable, even when the underlying calculation is correct.

**Required changes**

- Identify all transactions contributing to daily balance changes.
- Distinguish scheduled income, recurring income, bills, and predicted variable spending.
- Provide a breakdown when a significant balance change occurs.
- Allow users to inspect the underlying events for a particular date.
- Ensure the forecast chart and daily forecast table use consistent calculations.

**Acceptance criteria**

- Every significant balance change can be traced to identifiable financial events.
- The interface explains the November 17–18 increase.
- Daily balances reconcile with the starting balance and modeled inflows/outflows.
- No unexplained discontinuities remain in the forecast.

## P0.2 — Financial Health Score Lacks Transparency

**Observed behavior**

The dashboard displays:

- Financial health: 77.5 / 100.
- Financial health · legacy v1.
- Internal heuristic, not a credit score.
- Missing factors are excluded.
- Remaining weights are adjusted.

The user cannot determine what contributes to the score or how missing information affects the result.

**Why this matters**

A numerical financial health score creates an expectation of objective measurement. Without an explanation of its components, the score can be misleading.

**Required changes**

- Display the individual factors contributing to the score.
- Show each factor's assigned weight.
- Explain how missing information affects the calculation.
- Identify unavailable or excluded components.
- Clearly distinguish heuristic estimates from validated financial measurements.
- Avoid presenting the score as a definitive assessment.

**Acceptance criteria**

- Users can inspect the factors contributing to their score.
- Displayed weights and component values reconcile with the final score.
- Missing information is explicitly identified.
- The interface communicates that the score is an internal heuristic, not a credit score.

## P0.3 — Engineering Diagnostics Exposed in Customer-Facing UI

**Observed behavior**

The dashboard exposes internal implementation terminology:

- `forecast_unvalidated ? forecast`
- `legacy_score_partial ? analysis`
- `moving_average_28`
- `Backend category vocabulary differs from PNC training data`
- `Serving baseline has no applicable independent real-customer validation`

**Why this matters**

These messages expose implementation details that ordinary users do not need. They also make the application feel unfinished and distract from the actual financial insights.

**Required changes**

Separate developer diagnostics from customer-facing messaging.

Suggested wording:

| Existing terminology | Customer-facing replacement |
|---|---|
| `forecast_unvalidated` | Forecast is experimental |
| `moving_average_28` | Based on your recent spending patterns |
| `legacy_score_partial` | Some financial information is unavailable |
| Backend category vocabulary differs... | Some spending categories may be estimated |
| No independent real-customer validation | Forecast has not been independently validated |

Additionally:

- Keep technical diagnostic information in development-only tooling or a protected engineering diagnostics view.
- Do not expose internal enum values, implementation identifiers, or backend-specific terminology.
- Preserve meaningful limitations and warnings in user-friendly language.

**Acceptance criteria**

- No raw internal diagnostic identifiers appear in the normal dashboard.
- Technical information remains accessible to authorized developers.
- Customer-facing explanations accurately reflect the underlying system limitations.

---

# 3. Important Financial Logic & Information Issues (P1)

## P1.1 — Net Worth and Account Classification

**Observed behavior**

The dashboard displays:

| Metric | Amount |
|---|---:|
| Checking | $2,400 |
| Savings | $600 |
| Liabilities owed | $420 |
| Net worth | $2,580 |

The arithmetic is correct:

$2,400 + $600 - $420 = $2,580.

However, the presentation does not sufficiently distinguish assets from liabilities.

**Required changes**

- Group checking and savings under assets.
- Group credit card balances under liabilities.
- Clearly label net worth as assets minus liabilities.
- Distinguish account balances from amounts owed.
- Avoid presenting liabilities as positive available funds.

**Acceptance criteria**

The displayed net worth reconciles with the account and liability totals, and users can distinguish available assets from outstanding debt.

## P1.2 — Emergency Savings Warning Lacks Actionable Context

**Observed behavior**

Guardian displays:

"Liquid reserves cover fewer than three months of modeled outflows."

However, the dashboard does not provide the actual coverage period or explain the savings gap.

**Why this matters**

Identifying a financial risk is only the first step. The application should help users understand the size of the problem.

**Required changes**

Display:

- Current emergency fund balance.
- Estimated monthly essential expenses.
- Current emergency savings coverage in months.
- Recommended emergency savings target.
- Remaining amount needed to reach the target.

Use essential expenses rather than total discretionary spending when calculating the emergency fund target.

**Acceptance criteria**

- Coverage is calculated from clearly identified inputs.
- The target and remaining savings gap are visible.
- The calculation is consistent with the displayed account balances.
- Recommendations do not imply that transferring money between existing accounts increases total liquid reserves.

## P1.3 — Forecast Assumptions Need Better Explanation

**Observed behavior**

The forecast includes several technical explanations:

- Rolling-average plus historical-volatility heuristic.
- Stress envelopes.
- Scheduled income and bills.
- Backend category vocabulary differences.
- Forecast limitations.

Although technically useful, these explanations are not organized around what users need to understand.

**Required changes**

Organize forecast assumptions into a dedicated expandable section.

Include:

1. Forecast methodology in plain language.
2. Historical period used for spending estimates.
3. Scheduled income and bills included.
4. Assumptions about variable spending.
5. Explanation of low-stress and high-stress scenarios.
6. Limitations and validation status.

Explicitly distinguish stress scenarios from statistically calibrated confidence intervals.

**Acceptance criteria**

Users can understand how their forecast is generated without needing knowledge of the backend implementation.

---

# 4. Frontend UX and Presentation Issues

## P1.4 — Excessive Disclaimer Repetition

**Observed behavior**

The dashboard repeatedly communicates:

- Synthetic financial prototype.
- Not financial advice.
- Not a credit score.
- Missing data limitations.
- Forecast validation limitations.

**Why this matters**

Disclaimers are necessary, but repeating similar information throughout the page creates visual clutter and reduces the prominence of actual financial insights.

**Required changes**

- Maintain one prominent prototype and financial disclaimer.
- Keep contextual warnings near the specific feature they affect.
- Remove redundant disclaimer text.
- Preserve legally and functionally important disclosures.

**Acceptance criteria**

Every relevant limitation remains communicated, but duplicate messaging is eliminated.

## P1.5 — Weak Dashboard Information Hierarchy

**Observed behavior**

The Overview page contains numerous competing elements:

- Welcome message and mission statement.
- Data limitations.
- Engineering diagnostics.
- Account balances.
- Net worth.
- Upcoming bills.
- Spending categories.
- Financial health score.
- Guardian alerts.
- Predictive forecast.
- Forecast assumptions.
- Daily forecast table.

The most important financial information does not receive enough visual priority.

**Required changes**

Reorganize the dashboard into the following hierarchy:

**1. Financial Snapshot**
- Net worth.
- Checking and savings.
- Outstanding liabilities.
- Income and spending.

**2. Priority Financial Insights**
- Most important Guardian alert.
- Potential low-balance risks.
- Emergency savings status.

**3. Upcoming Obligations**
- Upcoming bills.
- Due dates.
- Amounts.

**4. Cash-Flow Forecast**
- Forecast chart.
- Lowest projected balance.
- Expected ending balance.
- Safety buffer.

**5. Detailed Analysis**
- Spending breakdown.
- Forecast assumptions.
- Detailed daily forecast.
- Additional financial health information.

The goal is to let users understand their financial situation within the first few seconds of opening the dashboard.

**Acceptance criteria**

- The most important financial information appears first.
- Related information is grouped logically.
- Secondary technical details do not compete with primary financial insights.
- The layout remains usable on desktop and mobile.

## P1.6 — Daily Forecast Table Overemphasized

**Observed behavior**

The dashboard displays a 30-day table containing:

- Date.
- Variable spending.
- Checking balance.
- Low-stress estimate.
- High-stress estimate.

This is useful for detailed analysis, but it consumes substantial dashboard space.

**Required changes**

- Keep the forecast chart as the primary visualization.
- Move the detailed daily forecast into an expandable section.
- Preserve access to all daily forecast values.
- Allow users to inspect specific dates and their associated financial events.
- Maintain consistency between the chart and table.

**Acceptance criteria**

The default dashboard presents the forecast visually, while users can expand the detailed table when needed.

---

# 5. Product Functionality Improvements

These are recommended enhancements rather than confirmed implementation defects.

## P1.7 — Explainable Financial Insights

FinPilot should explain not only what is happening but also why.

For example, instead of displaying:

"Projected checking falls below your chosen buffer."

Provide:

"Your checking balance is projected to fall below $500 on November 14 because of upcoming rent, utility payments, and your recent spending pattern."

**Recommended functionality**

- Identify contributing transactions and scheduled payments.
- Explain the cause of financial risks.
- Show the projected impact.
- Link insights to relevant financial data.

**Acceptance criteria**

Every major financial insight has an understandable explanation supported by underlying data.

## P1.8 — Actionable Guardian Recommendations

Guardian currently identifies:

- Low Balance.
- Emergency Savings.

The recommendations are primarily informational.

**Recommended functionality**

Allow users to compare financial scenarios.

Example:

- Current projected lowest balance: $358.50.
- Reduce discretionary spending by $100.
- Recalculate the forecast.
- Display the resulting projected lowest balance.

Additional considerations:

- Preserve essential payments.
- Show the assumptions behind each scenario.
- Allow comparison with the original forecast.
- Avoid suggesting transfers as new wealth.

**Acceptance criteria**

Users can modify a scenario and see how it changes their projected financial position without modifying their actual account data.

## P1.9 — AI Co-Pilot Should Use Actual Financial Data

FinPilot's AI Co-Pilot is an important product differentiator.

It should be capable of answering questions such as:

- Can I afford a $300 purchase next week?
- Why is my projected balance dropping?
- How much should I save each month?
- Which spending category increased the most?
- What happens if I reduce dining expenses by $100?

**Recommended functionality**

- Ground answers in the user's actual financial profile and forecast.
- Use structured financial calculations rather than relying solely on language-model estimation.
- Explain the reasoning behind recommendations.
- Identify missing information.
- Avoid inventing transactions or financial figures.
- Distinguish factual account information from hypothetical scenarios.

**Acceptance criteria**

AI-generated financial answers are traceable to available financial data and calculations.

## P2.0 — Historical Spending Comparisons

The dashboard currently displays category-level spending totals for the last 30 days.

It would be more useful to provide comparisons against previous periods.

**Recommended functionality**

- Current month versus previous month.
- Spending changes by category.
- Categories with the largest increases.
- Income versus spending trends.
- Historical cash-flow patterns.

**Acceptance criteria**

Historical comparisons use consistent date ranges and clearly identify whether changes are absolute or percentage-based.

---

# 6. Recommended Implementation Order

| Priority | Task | Primary area |
|---|---|---|
| P0 | Investigate forecast balance discontinuity | Backend + Frontend |
| P0 | Improve financial health score transparency | Backend + Frontend |
| P0 | Remove exposed engineering diagnostics | Frontend |
| P1 | Improve asset/liability presentation | Frontend |
| P1 | Improve emergency savings explanation | Backend + Frontend |
| P1 | Organize forecast assumptions | Frontend |
| P1 | Simplify dashboard hierarchy | Frontend |
| P1 | Move daily forecast table into expandable section | Frontend |
| P1 | Improve explainability of financial insights | Backend + Frontend |
| P1 | Add actionable Guardian scenarios | Backend + Frontend |
| P1 | Ground AI Co-Pilot in financial data | Backend + AI |
| P2 | Add historical spending comparisons | Backend + Frontend |

---

# 7. Engineering Verification Requirements

Before marking the remediation complete, verify the following.

### Financial correctness
- [ ] Net worth reconciles with assets and liabilities.
- [ ] Forecast balances reconcile with starting balances and daily cash flows.
- [ ] Large balance changes have identifiable contributing events.
- [ ] Emergency savings calculations use essential expenses.
- [ ] Financial health score components reconcile with the final score.
- [ ] Missing data is handled consistently.

### Frontend quality
- [ ] No raw engineering diagnostics appear in customer-facing views.
- [ ] Disclaimers are not unnecessarily duplicated.
- [ ] Primary financial information has clear visual priority.
- [ ] Forecast chart and daily table display consistent data.
- [ ] Expandable sections work correctly.
- [ ] Desktop and mobile layouts remain usable.

### AI and recommendations
- [ ] Financial answers use actual available financial data.
- [ ] Recommendations can be traced to underlying calculations.
- [ ] Hypothetical scenarios do not modify actual account data.
- [ ] Missing information is disclosed.
- [ ] AI responses do not invent financial transactions or figures.

---

# 8. Scope and Implementation Guidance

This report is based on the deployed Overview dashboard and its visible content.

The following have not yet been independently inspected or tested:

- My Finances.
- Forecasts.
- Health Score.
- Guardian.
- Digital Twin.
- Economic Lab.
- AI Co-Pilot.
- FinPilot Wrapped.

Do not assume these sections have the same defects.

**Instructions for implementation:**

1. Inspect the existing frontend and backend implementation before modifying code.
2. Trace the source of each displayed financial value to its underlying calculation.
3. Reproduce and verify suspected calculation issues before changing business logic.
4. Reuse existing data models and calculation services where appropriate.
5. Avoid introducing duplicate financial calculations in the frontend.
6. Add or update automated tests for corrected financial calculations.
7. Preserve existing functionality unless a change is explicitly required.
8. Validate the deployed result against the acceptance criteria in this report.

**Final objective**

Transform FinPilot's Overview dashboard into a professional, explainable financial intelligence interface.

The application should consistently answer three questions:

1. What is happening with my finances?
2. What is likely to happen next?
3. What should I do about it, and why?

Financial accuracy, explainability, and user trust should take precedence over adding more dashboard features.
