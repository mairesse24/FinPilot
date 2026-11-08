# Executed economic vintage replay

| as_of | period | status | dimensions | Sahm_computed | Sahm_official | GDP_qoq_annualized | signals |
|---|---|---|---|---|---|---|---|
| 2008-10-31 | financial crisis | Mixed Signals | 4.0000 | 1.2667 | N/A | -0.2522 | PCE inflation above 2% objective; PCE inflation accelerating; Sahm recession indicator triggered; Real GDP contraction; Industrial output decline; Nominal retail decline |
| 2009-03-31 | financial crisis trough period | Mixed Signals | 4.0000 | 2.7667 | N/A | -6.3424 | Sahm recession indicator triggered; Real GDP contraction; Industrial output decline; Nominal retail decline |
| 2020-04-30 | COVID shock | Mixed Signals | 5.0000 | 0.3000 | 0.3000 | -4.7831 | Claims rising relative to prior weeks; Real GDP contraction; Industrial output decline; Nominal retail decline; VIX above prior 90th percentile |
| 2022-06-30 | inflation acceleration | Multiple pressure signals | 5.0000 | -0.0667 | -0.0700 | -1.5734 | PCE inflation above 2% objective; PCE inflation accelerating; Claims rising relative to prior weeks; Real GDP contraction; Policy rate rising; VIX above prior 90th percentile |
| 2023-07-31 | monetary tightening | Mixed Signals | 5.0000 | 0.0667 | 0.0700 | 2.4143 | PCE inflation above 2% objective; Industrial output decline; Yield curve inverted; Policy rate rising |
| 2017-06-30 | comparison expansion period | Mixed Signals | 5.0000 | -0.1333 | N/A | 1.4231 | Policy rate rising |

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
24 successful source series and 0 provider errors.
The current pressure status is `Mixed Signals`; data dates and metadata
are in `current_classification.json` and `indicator_catalog.csv`. These are real
retrieved data, not demonstration values. Historical raw caches remain local and
versioned; latest display pointer was restored after replay.
