"""Separate retrospective household and equity experiments, with explicit abstention."""
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, balanced_accuracy_score, brier_score_loss

FEATURES = ['inflation_lag', 'inflation_change', 'unemployment_lag', 'unemployment_change',
            'rate_lag', 'return_1m', 'return_3m', 'volatility_3m']


def monthly_features(raw, as_of):
    """Use complete calendar months, two-month macro publication lag, no backfill."""
    f = raw.copy()
    f.index = pd.to_datetime(f.index)
    if f.index.has_duplicates or not f.index.is_monotonic_increasing:
        raise ValueError('Economic history must be sorted with unique dates')
    end = pd.Timestamp(as_of)
    f = f.loc[f.index <= end, ['CPIAUCSL', 'UNRATE', 'FEDFUNDS', 'SP500']]
    # Reindex to calendar months; never fill a missing month with a future observation.
    m = f.resample('ME').last()
    m = m.loc[m.index <= end]
    cpi = m.CPIAUCSL
    inflation = (cpi/cpi.shift(12)-1)*100
    returns = m.SP500/m.SP500.shift(1)-1
    result = pd.DataFrame(index=m.index)
    result['inflation_lag'] = inflation.shift(2)
    result['inflation_change'] = inflation.diff(3).shift(2)
    result['unemployment_lag'] = m.UNRATE.shift(2)
    result['unemployment_change'] = m.UNRATE.diff(3).shift(2)
    result['rate_lag'] = m.FEDFUNDS.shift(2)
    result['return_1m'] = returns
    result['return_3m'] = m.SP500/m.SP500.shift(3)-1
    result['volatility_3m'] = returns.rolling(3).std()
    result['next_inflation'] = inflation.shift(-1)
    result['next_unemployment'] = m.UNRATE.shift(-1)
    # Unknown final return remains NaN rather than being mislabeled "down".
    result['next_return'] = m.SP500.shift(-1)/m.SP500-1
    result['target_month'] = result.index + pd.offsets.MonthEnd(1)
    return result.replace([np.inf, -np.inf], np.nan).dropna(subset=FEATURES)


def research_outlook(raw, as_of):
    f = monthly_features(raw, as_of)
    if len(f) < 72:
        raise ValueError('Need at least 72 usable monthly feature rows')
    latest = f.iloc[[-1]]
    report = {'as_of': str(as_of), 'feature_month': str(f.index[-1].date()),
              'target_month': str(latest.target_month.iloc[0].date()),
              'data_basis': 'current-revised FRED history with conservative two-month macro lags',
              'point_in_time_validated': False,
              'limitations': ['Current revised data can contain revisions unavailable at historical forecast dates.',
                             'Not a tradable backtest; no dividends, costs, or live execution.',
                             'Household results forecast national indicators, not an individual household or job loss.',
                             'Small monthly evaluation sample; no calibrated probabilities.'],
              'household': {}}
    # Fixed predeclared final 24 months; expanding fits and release-aware label eligibility.
    for target, baseline in [('next_inflation', 'inflation_lag'), ('next_unemployment', 'unemployment_lag')]:
        labeled = f.dropna(subset=[target])
        predicted, actual, naive = [], [], []
        for i in range(max(48, len(labeled)-24), len(labeled)):
            origin = labeled.index[i]
            # Monthly macro outcomes are not known at their observation-month end.
            eligible = labeled.iloc[:i]
            eligible = eligible[eligible.target_month + pd.offsets.MonthEnd(2) <= origin]
            model = make_pipeline(StandardScaler(), Ridge(alpha=10))
            model.fit(eligible[FEATURES], eligible[target])
            predicted.append(float(model.predict(labeled.iloc[[i]][FEATURES])[0]))
            actual.append(float(labeled.iloc[i][target]))
            naive.append(float(labeled.iloc[i][baseline]))
        eligible = labeled[labeled.target_month + pd.offsets.MonthEnd(2) <= latest.index[0]]
        model = make_pipeline(StandardScaler(), Ridge(alpha=10)).fit(eligible[FEATURES], eligible[target])
        estimate = float(model.predict(latest[FEATURES])[0])
        mae, naive_mae = mean_absolute_error(actual, predicted), mean_absolute_error(actual, naive)
        report['household'][target] = {'ridge_estimate_pct': round(estimate, 3),
            'persistence_estimate_pct': round(float(latest[baseline].iloc[0]), 3),
            'evaluation_months': len(actual), 'mae_percentage_points': round(mae, 4),
            'persistence_mae_percentage_points': round(naive_mae, 4),
            'beats_persistence': bool(mae < naive_mae),
            'recommended_display': 'persistence_baseline_until_point_in_time_validation',
            'status': 'research_only_pending_vintage_validation'}

    labeled = f.dropna(subset=['next_return'])
    p, y, base, momentum = [], [], [], []
    for i in range(max(48, len(labeled)-24), len(labeled)):
        train, test = labeled.iloc[:i], labeled.iloc[[i]]
        labels = (train.next_return > 0).astype(int)
        prior = float(labels.mean())
        model = make_pipeline(StandardScaler(), LogisticRegression(C=.1, max_iter=1000))
        if labels.nunique() < 2:
            probability = prior
        else:
            model.fit(train[FEATURES], labels)
            probability = float(model.predict_proba(test[FEATURES])[0, 1])
        p.append(probability)
        y.append(int(test.next_return.iloc[0] > 0))
        base.append(prior)
        momentum.append(int(test.return_3m.iloc[0] > 0))
    model_score = balanced_accuracy_score(y, np.array(p) >= .5)
    prior_score = balanced_accuracy_score(y, np.array(base) >= .5)
    momentum_score = balanced_accuracy_score(y, momentum)
    labels = (labeled.next_return > 0).astype(int)
    if labels.nunique() < 2:
        probability = float(labels.mean())
    else:
        model = make_pipeline(StandardScaler(), LogisticRegression(C=.1, max_iter=1000)).fit(labeled[FEATURES], labels)
        probability = float(model.predict_proba(latest[FEATURES])[0, 1])
    beats = model_score > max(prior_score, momentum_score) and brier_score_loss(y, p) < brier_score_loss(y, base)
    report['market'] = {'target': 'next calendar month S&P 500 price return > 0',
        'experimental_up_probability': round(probability, 4), 'probability_calibrated': False,
        'evaluation_months': len(y), 'balanced_accuracy': round(model_score, 4),
        'historical_prior_balanced_accuracy': round(prior_score, 4),
        'momentum_balanced_accuracy': round(momentum_score, 4),
        'brier_score': round(brier_score_loss(y, p), 4),
        'historical_prior_brier_score': round(brier_score_loss(y, base), 4),
        'beats_baselines': bool(beats), 'direction': 'abstain',
        'reason': 'Requires point-in-time vintage validation before releasing a directional signal.' if beats else 'Does not beat predeclared baseline gates; no supported directional signal.'}
    return report
