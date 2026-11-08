# FinPilot financial health methodology v2

This is a **FinPilot-defined provisional designed index**, not the CFPB Financial
Well-Being Scale, credit score, scientifically optimal weights or validated risk
probability. Legacy `/api/health` and original v1 definitions remain available;
the new UI and `/api/financial-health` explicitly identify v2.

## Evidence and choices

[CFPB's scale](https://www.consumerfinance.gov/data-research/research-reports/financial-well-being-scale/)
is a validated questionnaire instrument; its questionnaire scoring cannot be
transferred to transactions. [CFPB emergency guidance](https://www.consumerfinance.gov/an-essential-guide-to-building-an-emergency-fund/)
explains that needs depend on the household. [FDIC guidance](https://www.fdic.gov/consumer-resource-center/2025-01/saving-unexpected-and-your-future)
provides contextual six-month reserves guidance. None validates our composite
weights or transforms. [CFPB DTI](https://www.consumerfinance.gov/ask-cfpb/what-is-a-debt-to-income-ratio-en-1791/)
uses gross income; a take-home payment ratio is labeled separately here.

Equal weighting is chosen provisionally because no validated account-derived
outcome labels or applicable optimal weights are available. Research-informed
weights risk implying nonexistent validation; expert weights remain judgment;
data-driven weights need outcomes and independent testing. The selected four
dimensions each get **25%**, explicitly a product assumption. All four must be
available; the total is withheld rather than renormalizing missing dimensions.
Financial stability/variability is a diagnostic, not an additional score that
double-counts reserve coverage or automatically penalizes irregular workers.

## Inputs and ledger definitions

Imported owned checking/savings balances, liabilities, credit limits, bills,
recurrences and classified transactions are bank-profile inputs. Confirmed facts
are **user-supplied assumptions**, not independently verified bank observations:
monthly take-home income, essential **non-debt** cash expenses, discretionary cash
expenses, required debt payments, accessible emergency savings, bill/debt completeness,
optional gross income, optional variable-rate debt and investment exposures.
Missing fields remain null. Confirming complete debt information can establish
zero debt; an absent debt account alone cannot. Unlinked ambiguous account
minimums/bills do not silently produce exact debt totals.

Essential budgets include rent, utilities, food and insurance, but exclude debt
payments; mortgage/loan/card required payments belong in the debt field once.
Discretionary budgets exclude savings transfers. Card purchases are consumption;
repayment is settlement, not a second purchase. The cash budget uses checking
outflows and repayment obligations consistently. Internal transfers are not new
income, expenses or net worth. Voluntary extra principal is distinct from a
required payment and does not automatically change future contractual minimums.

## Every component formula

Let C=checking, S=confirmed accessible savings (capped by imported savings),
I=confirmed take-home income, E=essential non-debt outflows, X=discretionary cash
outflows, D=required monthly debt payments. Let B be known bills due through the
next expected income date, capped at 30 days (30 days if no income event exists).
Bills on payday are conservatively before the deposit. Eligible emergency funds:
`R=max(0, S-max(0,B-max(0,C)))`. This excludes reserves already needed to cover
imminent checking shortfalls. Unknown bill completeness withholds R/readiness.

| Component | Formula | Decision origin |
|---|---|---|
| Emergency preparedness | months=R/(E+D); score=100*clip(months/6,0,1) | Six months contextual guidance; linear mapping is product judgment |
| Cash-flow sustainability | outflows=E+X+max(D,scheduled debt); surplus=I-outflows; score=100*I/(I+outflows) | Smooth bounded product mapping, 50 at break-even |
| Debt affordability | ratio=D/I; score=100*max(0,I-D)/I | Remaining take-home share; product score, not gross DTI |
| Payment readiness | 100*min(1,max(0,C)/B); 100 if confirmed complete B=0 | Known-schedule liquidity ratio; no ML authority |

Undefined denominators yield null, not infinity or a perfect score. Confirmed
zero income with positive outflows has sustainability 0; zero-income/zero-debt
affordability is undefined. Essential obligations include required debt for
emergency coverage, but monthly cash totals include each obligation only once.
Checking and uncommitted savings are separate for readiness and emergency funds.
Debt also affects sustainability: these are correlated vulnerability dimensions,
not independent statistical factors. Equal weights are not causal coefficients.

Scheduled debt above the confirmed required amount is a separate cash outflow,
not added twice: cash outflows are E+X+D+max(0,scheduled debt-D). It may represent
voluntary extra payment or unclassified settlement, not an inferred contractual
minimum. Confirmed budgets cannot omit known recurring non-debt bills or fall
below known account minimums. If required debt exceeds dated debt schedules,
readiness and uncommitted reserves are withheld pending payment dates.

Total is the mean of four displayed component scores, rounded to two decimals,
only at 100% component completeness. All transforms are deterministic and bounded.
Scores are comparable only within v2 and with consistent complete-input definitions.
75/50 thresholds for strengths/improvement labels are product display policies.

## Diagnostics, missingness and sensitivity

Credit utilization is the sum of nonnegative revolving balances divided by reliable
total revolving limits; loans are excluded and missing limits => null. Above-100%
utilization is allowed as an observed over-limit ratio, not clipped or invented.
Gross DTI is reported only with confirmed gross income; take-home burden stays
separate. Income variability requires confirmed coverage of six complete months;
the calendar-month coefficient of variation is diagnostic only and includes pay-
calendar effects such as three-biweekly-paycheck months. It never directly lowers
the composite. Cash reserves and payment coverage contextualize irregular income.

Cash surplus / take-home income is labeled a **cash surplus rate**, not net wealth
creation. True net income-attributable savings rate is withheld because current
balance snapshots/transfer records do not identify it. No fabricated historical
savings rate is produced. Restricted/unknown-access savings are not assumed eligible.
Optional exposures never change baseline health because markets or rates moved.

Weight sensitivity varies each component from 25% to 20%/30%, redistributing the
remaining weight equally. Input sensitivity varies one factor at a time. See
FINANCIAL_SCORE_VALIDATION.md. Known obligations plus confirmed budget assumptions,
not unreliable multi-day ML forecasts, drive payment readiness and stress planning.
