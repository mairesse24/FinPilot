"""Render research/methodology and actual executed validation artifacts."""
import json
import xml.etree.ElementTree as ET
from pathlib import Path
import pandas as pd
from backend.intelligence.economic_data import ROOT,cached,CATALOG,TICKERS
from backend.intelligence.regimes import classify
from scripts.evaluate_ml import table

DOCS=ROOT/'docs';REPORTS=ROOT/'reports/economic_intelligence'


def main():
    snapshot=cached();as_of=snapshot.get('as_of','2026-11-07');conditions=classify(snapshot,as_of)
    catalog=[]
    for identifier in CATALOG:
        source=snapshot.get('series',{}).get(identifier)
        latest=source['observations'][-1] if source and source.get('observations') else None
        catalog.append({'series':identifier,'publisher':CATALOG[identifier][1],
            'units':source.get('units','Unavailable') if source else 'Unavailable',
            'frequency':source.get('frequency',CATALOG[identifier][0]) if source else CATALOG[identifier][0],
            'adjustment':source.get('seasonal_adjustment','Unknown') if source else 'Unknown',
            'latest_observation':latest['date'] if latest else 'Unavailable','value':latest['value'] if latest else None,
            'initial_release_date':source.get('initial_release_date') if source else None,'knowledge_date':source.get('knowledge_date') if source else None})
    pd.DataFrame(catalog).to_csv(REPORTS/'indicator_catalog.csv',index=False)
    (REPORTS/'current_classification.json').write_text(json.dumps(conditions,indent=2,allow_nan=False))
    DOCS.mkdir(exist_ok=True)
    (DOCS/'ECONOMIC_INDICATORS.md').write_text(f'''# Economic indicators and ingestion

Actual refresh: as-of {as_of}; {len(snapshot.get('series',{}))} series available.
FRED key stays in root/backend `.env` as `FRED_API_KEY`. Yahoo does not use this key.

{table(pd.DataFrame(catalog))}

Every series has its own source page `https://fred.stlouisfed.org/series/SERIES_ID`.
Metadata and units are queried from the official API with the same real-time
date as the observations. Values are not assumed daily when the series is monthly
or quarterly. Publication date, observation period and retrieval time differ.
The initial-release date of the latest observation is separately requested using
`output_type=4` where available. Exact intraday release timestamps are unknown,
not fabricated. Historical `knowledge_date` means available in that official
vintage by end of that day; it does not mean first published that day.

Release interpretation: CPI/core CPI and unemployment are BLS monthly releases;
PCE is BEA Personal Income and Outlays; GDP is BEA's quarterly estimate/revision
sequence; claims are weekly Department of Labor releases. Fed rates/yields,
credit spreads and VIX each retain their native frequencies and update metadata.
Exact dates come from retrieved vintage/initial-release records, never from the
first day of an observation period. Consult each linked publisher release calendar
for intraday use; this implementation is end-of-day only.

The price indices support YoY and separate MoM rates. UNRATE and ICSA describe
labor conditions; FEDFUNDS, Treasury yields and spreads describe policy/credit;
INDPRO and RSAFS describe industrial/nominal retail momentum; GDPC1 is real GDP
at a seasonally adjusted annual rate. BAMLH0A0HYM2 is an option-adjusted spread
in percentage points, not a default probability. SAHMREALTIME is the published
real-time rule. SP500/VIXCLS are optional official historical market evidence;
missing historical vintages are explicitly omitted.

Yahoo investigated tickers: {', '.join(TICKERS)}. All successful downloads retain
adjusted closes and source/retrieval metadata. SPY is the primary adjusted equity
proxy; ^GSPC is a price-index fallback. ^IXIC and ^DJI do not get extra votes for
the same equity movement. AGG is used for equity/bond divergence; TLT is duration
context; ^VIX is implied volatility, not realized volatility. ^TNX is retained
as a raw yield proxy and not substituted for official DGS10 or assumed to use
an unverified scaling convention.

Sources: [official FRED API](https://fred.stlouisfed.org/docs/api/fred/),
[observations/vintages](https://fred.stlouisfed.org/docs/api/fred/series_observations.html),
[metadata](https://fred.stlouisfed.org/docs/api/fred/series.html),
[yfinance documentation and terms limitations](https://ranaroussi.github.io/yfinance/),
[Cboe VIX definition](https://www.cboe.com/tradable_products/vix/faqs).
yfinance is an unofficial research/personal-use integration, not an endorsed
production market-data contract. A production alternative is a licensed exchange/
index vendor or broker feed; acquisition rights and historical adjustment vintages
must be verified. FRED SP500/VIXCLS can provide a limited official-source fallback,
not equivalent adjusted ETF total returns. Raw caches are ignored by Git to avoid
redistributing licensed market histories without reviewing terms.

`economic_data.py` uses bounded retries/backoff, Retry-After handling, three FRED
workers and a shared 0.55-second request pace. Nonfinite, duplicate, empty and
truncated histories are rejected. Missing FRED values remain missing. Versioned
JSON caches are separate by vintage/retrieval time; no network refresh occurs
inside dashboard requests. API keys and authenticated request URLs are never
printed. Observation dates are calendar dates; retrieval timestamps are UTC;
client as-of dates use America/Chicago. No forward-fill supplies missing macro
values. Age is always displayed; stale observations are excluded from decisions.

Refresh from root: `.venv/Scripts/python.exe -m scripts.refresh_intelligence`.
Historical refresh: add `--as-of YYYY-MM-DD --fred-only`.
Unavailable providers produce explicit errors without generated substitute values.
''',encoding='utf-8')
    (DOCS/'ECONOMIC_CLASSIFICATION_METHODOLOGY.md').write_text('''# Economic classification methodology v2

This is a descriptive rule system, not a trained classifier, recession forecast,
stock prediction or calibrated probability. Multiple conditions can coexist.
Existing Ridge/logistic research and LightGBM weights are unchanged.

## Methods considered

Transparent published-rule baselines are auditable and have clear units.
Standardized composites require historical normalization and chosen weights;
they can hide correlated indicator votes and introduce lookahead if fit globally.
Gaussian mixtures/HMMs can discover clusters but do not establish economic labels,
are sensitive to scaling/sample periods and need vintage-safe stability testing.
Supervised regimes require legitimate reference labels and outcome definitions.
None of these learned approaches was promoted without evidence. No economic
classification accuracy or confusion matrix is claimed from selected episodes.

## Transformations

- Monthly price index YoY: `100*(I[t]/I[t-12]-1)`; MoM: `100*(I[t]/I[t-1]-1)`.
  Acceleration is current YoY minus YoY three months earlier, in percentage points.
  Missing calendar months invalidate needed transformations; no future backfill.
- PCE YoY is compared with the Fed's **2% longer-run PCE objective**, not CPI.
  Above 2 and acceleration above 0 are descriptive signs, not empirically fitted
  danger boundaries. CPI/core CPI are separate diagnostic rates.
- Sahm: `MA3(UNRATE)[t] - min(MA3[ t-12 : t-1 ])`, requiring all 12 prior
  three-month means. The published signal boundary is **0.50 percentage points**.
  Prefer the official SAHMREALTIME series when available. A computed value from
  one vintage is not mixed with later revised observations. Declining unemployment
  can yield a negative statistic; it is not clipped to zero.
- Claims: four-week mean versus the preceding 13-week mean, expressed as a
  percentage change. A positive direction is descriptive, not a published recession
  threshold or a job-loss probability.
- GDP: `100*((GDP[q]/GDP[q-1])**4-1)`, annualized quarter-on-quarter growth.
  Industrial production and nominal retail sales use separate 3-month percentage
  changes. Negative growth indicates contraction in that series; it is not an
  NBER recession declaration. Nominal retail sales are not real output.
- Monetary/credit: negative T10Y2Y means inversion, not automatic recession.
  FEDFUNDS change over three months describes rising policy rates; 10-year yield
  change uses 63 observed daily sessions and remains a separate diagnostic.
  High-yield spreads above their prior 90th percentile are a **product rule**,
  computed from up to 2520 prior available observations, at least 252.
- Market: 63-session equity returns; 252-session drawdown; annualized 20-session
  log-return standard deviation (`sqrt(252)` trading-day convention); deviation
  from prior volatility/VIX 90th percentiles; equity minus AGG return. A 10%
  drawdown flag is a descriptive product boundary. Yahoo SPY includes current
  adjustment information; ^GSPC is explicitly a price-index alternative.

## Taxonomy, weighting and evidence

Five dimensions: inflation, labor, growth, monetary/credit and market stress.
Each dimension reports availability, signals, explanation, numerical features,
source observation date and knowledge date. No redundant equity-index voting.
Labels coexist. Fewer than 3 supported dimensions => Insufficient Data. A mix
of flagged and unflagged dimensions => Mixed Signals. No flags means only
No configured pressure signals, never guaranteed economic health.

Pressure breadth is `100 * flagged available dimensions / available dimensions`,
withheld unless at least 4/5 dimensions are supported. Equal dimension votes,
minimum coverage and taxonomy are transparent FinPilot product assumptions.
The index is not a statistically estimated severity score or probability.
Correlated sub-indicators do not receive additional dimension votes.

Freshness cutoffs are product data-quality policies: daily FRED 10 calendar days,
Yahoo 7, weekly claims 21, monthly 75 or 100 by series, GDP 200. Stale values may
be displayed with age but are excluded from feature decisions. Monthly rates
are not relabeled daily. All historical classification requires an official
as-of vintage and discards future availability dates and non-PIT Yahoo history.
This is end-of-day availability, not an intraday release simulation.

Sources: [Federal Reserve objective](https://www.federalreserve.gov/faqs/economy_14400.htm),
[official Sahm definition](https://fred.stlouisfed.org/series/SAHMREALTIME),
[FRED vintage API](https://fred.stlouisfed.org/docs/api/fred/series_observations.html),
[Cboe VIX](https://www.cboe.com/tradable_products/vix/faqs).
''',encoding='utf-8')
    (DOCS/'FINANCIAL_HEALTH_SCORING_METHODOLOGY.md').write_text('''# FinPilot financial health methodology v2

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
''',encoding='utf-8')
    history=json.loads((REPORTS/'historical_regimes.json').read_text())
    historical=pd.DataFrame([{'as_of':r['as_of'],'period':r['period'],'status':r['status'],
        'dimensions':r['evidence_quality']['available_dimensions'],'Sahm_computed':r['features'].get('sahm_computed_pp'),
        'Sahm_official':r['features'].get('sahm_official_pp'),'GDP_qoq_annualized':r['features'].get('gdp_qoq_annualized_pct'),
        'signals':'; '.join(r['labels'])} for r in history])
    historical.to_csv(REPORTS/'historical_summary.csv',index=False)
    (DOCS/'ECONOMIC_BACKTEST_REPORT.md').write_text(f'''# Executed economic vintage replay

{table(historical)}

These classifications were executed from official FRED/ALFRED vintage requests
at each listed end-of-day origin. Yahoo was excluded. Unavailable historical
series/vintages are retained as errors in `reports/economic_intelligence/historical_regimes.json`,
not replaced by revised current histories. 2008/2009 lack historical market
coverage; later episodes have five dimension groups supported. Some ICE/SP500
vintages remain unavailable even when a related current series is available.

This is interpretability/availability validation, **not predictive accuracy**.
No genuine supervised regime target or calibrated regime probabilities were
introduced, so no classification accuracy/confusion matrix is fabricated.
The selected episodes do not establish stability over every economic cycle.
Sahm computed values agree with available official values to their published
two-decimal precision in these replay rows. Some earlier official Sahm series
vintages are unavailable; those rows use only the explicitly computed rule.

April 30, 2020 cannot use April unemployment published in May. GDP at each origin
is the then-available vintage, not later revised growth. The current cache also
contains a missing October 2025 UNRATE value; computed Sahm is withheld rather
than filled, while the separately published Sahm statistic can still be shown.

Commands actually run: `python -m scripts.refresh_intelligence --as-of 2026-11-07`,
`python -m scripts.backtest_economic_regimes`. Current snapshot has
{len(snapshot.get('series',{}))} successful source series and {len(snapshot.get('errors',{}))} provider errors.
The current pressure status is `{conditions['status']}`; data dates and metadata
are in `current_classification.json` and `indicator_catalog.csv`. These are real
retrieved data, not demonstration values. Historical raw caches remain local and
versioned; latest display pointer was restored after replay.
''',encoding='utf-8')
    profiles=pd.read_csv(REPORTS/'financial_profiles.csv');sensitivity=pd.read_csv(REPORTS/'score_sensitivity.csv');weights=pd.read_csv(REPORTS/'weight_sensitivity.csv')
    tests=REPORTS/'tests.xml';summary='Tests not executed.'
    if tests.exists():
        cases=ET.parse(tests).getroot().findall('.//testcase');skipped=sum(c.find('skipped') is not None for c in cases);failed=sum(c.find('failure') is not None or c.find('error') is not None for c in cases)
        summary=f'Executed full suite: {len(cases)-skipped-failed} passed, {skipped} skipped, {failed} failed.'
    (DOCS/'FINANCIAL_SCORE_VALIDATION.md').write_text(f'''# Financial score validation

{summary}

The property loop checks 200 reproducible input combinations (seed 42).
These test mathematical consistency and safety, not score accuracy against an
invented ground truth. Explicit invariants cover 0–100 bounds, finite JSON,
missing inputs, monotonic savings/essential/debt effects, small perturbations,
net-worth conservation for transfers and principal repayment, cash-only repayment
settlement, missing credit limits, no automatic fixed-debt repricing, no market
markdown of checking, deterministic repeated inputs and macro-independent health.
Temporal tests reject future releases, stale data and unverified historical Yahoo.
Mock HTTP tests cover bounded retries/redaction. Live FRED/Yahoo results and
historical replay are separate from mocked provider tests. No paid LLM call is
used to validate financial arithmetic.

Representative **synthetic** profiles with declared assumptions:

{table(profiles)}

One-factor sensitivity (debt perturbations use a $200 debt-payment baseline):

{table(sensitivity)}

Weight changes of ±5 percentage points produced total-score changes ranging
from {weights.difference.min():.4f} to {weights.difference.max():.4f} points across these
profiles. Full alternatives are in `weight_sensitivity.csv`. This material
sensitivity is another reason to label the weights provisional, not scientifically
optimal. Missing scores are intentionally withheld, not NaN API values.

Limitations: confirmed inputs can still be inaccurate user statements; source
coverage is limited to imported accounts; no validated well-being outcome labels;
no official CFPB questionnaire equivalence; imperfect bill completeness; no
restricted-fund knowledge without confirmation; no full historical savings-rate
ledger; calendar-month income CV includes pay-frequency effects and is not scored.
Historical score-change attribution requires stored historical assessments, which
are not yet persisted; the UI instead explains current formulas and explicit
before/after scenario changes. No retroactive score history is invented.

Reproduce with `python -m scripts.validate_financial_score`, `python -m pytest`,
and `python -m scripts.document_economic_engine`. API integration uses scoped
profiles, confirmed facts and deterministic stress responses. Existing v1 score
endpoint remains unchanged and is explicitly labeled legacy in the UI/chat.
''',encoding='utf-8')
    print('Wrote all five methodology/validation documents from actual artifacts.')


if __name__=='__main__':main()
