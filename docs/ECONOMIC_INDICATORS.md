# Economic indicators and ingestion

Actual refresh: as-of 2026-11-07; 24 series available.
FRED key stays in root/backend `.env` as `FRED_API_KEY`. Yahoo does not use this key.

| series | publisher | units | frequency | adjustment | latest_observation | value | initial_release_date | knowledge_date |
|---|---|---|---|---|---|---|---|---|
| CPIAUCSL | BLS | Index 1982-1984=100 | Monthly | Seasonally Adjusted | 2026-09-01 | 336.2980 | 2026-10-14 | 2026-11-07 |
| CPILFESL | BLS | Index 1982-1984=100 | Monthly | Seasonally Adjusted | 2026-09-01 | 338.8960 | 2026-10-14 | 2026-11-07 |
| PCEPI | BEA | Index 2017=100 | Monthly | Seasonally Adjusted | 2026-09-01 | 132.2570 | 2026-10-29 | 2026-11-07 |
| UNRATE | BLS | Percent | Monthly | Seasonally Adjusted | 2026-10-01 | 4.1000 | 2026-11-06 | 2026-11-07 |
| ICSA | US Department of Labor | Number | Weekly, Ending Saturday | Seasonally Adjusted | 2026-10-31 | 189000.0000 | 2026-11-05 | 2026-11-07 |
| FEDFUNDS | Federal Reserve Board | Percent | Monthly | Not Seasonally Adjusted | 2026-10-01 | 3.8800 | 2026-11-02 | 2026-11-07 |
| DGS10 | Federal Reserve Board | Percent | Daily | Not Seasonally Adjusted | 2026-11-05 | 4.8400 | nan | 2026-11-07 |
| DGS2 | Federal Reserve Board | Percent | Daily | Not Seasonally Adjusted | 2026-11-05 | 4.4600 | nan | 2026-11-07 |
| T10Y2Y | Federal Reserve Bank of St. Louis | Percent | Daily | Not Seasonally Adjusted | 2026-11-06 | 0.3500 | nan | 2026-11-07 |
| INDPRO | Federal Reserve Board | Index 2017=100 | Monthly | Seasonally Adjusted | 2026-09-01 | 103.9506 | 2026-10-16 | 2026-11-07 |
| RSAFS | US Census Bureau | Millions of Dollars | Monthly | Seasonally Adjusted | 2026-09-01 | 745021.0000 | 2026-10-15 | 2026-11-07 |
| GDPC1 | BEA | Billions of Chained 2017 Dollars | Quarterly | Seasonally Adjusted Annual Rate | 2026-07-01 | 24611.0770 | 2026-10-29 | 2026-11-07 |
| BAMLH0A0HYM2 | ICE Data Indices | Percent | Daily, Close | Not Seasonally Adjusted | 2026-11-05 | 3.4800 | 2026-11-05 | 2026-11-07 |
| SAHMREALTIME | Claudia Sahm | Percentage Points | Monthly | Seasonally Adjusted | 2026-10-01 | 0.0000 | 2026-11-06 | 2026-11-07 |
| SP500 | S&P Dow Jones Indices | Index | Daily, Close | Not Seasonally Adjusted | 2026-11-05 | 7353.7300 | nan | 2026-11-07 |
| VIXCLS | CBOE | Index | Daily, Close | Not Seasonally Adjusted | 2026-11-05 | 28.1800 | nan | 2026-11-07 |

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

Yahoo investigated tickers: ^GSPC, ^IXIC, ^DJI, ^VIX, ^TNX, SPY, AGG, TLT. All successful downloads retain
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
