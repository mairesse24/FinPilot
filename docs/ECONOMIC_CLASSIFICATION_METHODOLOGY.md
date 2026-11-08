# Economic classification methodology v2

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
