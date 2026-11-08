"""Leakage-safe daily features: every spending statistic is shifted before rolling."""
import pandas as pd

FEATURES = ['weekday', 'day', 'month', 'payday_distance', 'lag_1', 'lag_7', 'lag_28',
            'mean_7', 'mean_28', 'std_28', 'calendar_lag_1', 'calendar_mean_3']


def make_features(daily):
    frames = []
    for _, group in daily.groupby('customer_id'):
        g = group.sort_values('date').copy()
        dates = pd.to_datetime(g.date)
        g['weekday'], g['day'], g['month'] = dates.dt.day_of_week, dates.dt.day, dates.dt.month
        # Training dataset has synthetic semi-monthly payroll; inference uses same calendar feature.
        g['payday_distance'] = g.day.map(lambda d: min(abs(d-1), abs(d-15), abs(d-28)))
        for lag in (1, 7, 28):
            g[f'lag_{lag}'] = g.spending.shift(lag)
        previous = g.spending.shift(1)
        g['mean_7'] = previous.rolling(7).mean()
        g['mean_28'] = previous.rolling(28).mean()
        g['std_28'] = previous.rolling(28).std()
        lookup = pd.Series(g.spending.to_numpy(), index=pd.DatetimeIndex(dates))
        calendar_values = pd.DataFrame({m: (dates-pd.DateOffset(months=m)).map(lookup)
                                        for m in (1, 2, 3)})
        g['calendar_lag_1'] = calendar_values[1].fillna(g['mean_28'])
        g['calendar_mean_3'] = calendar_values.mean(axis=1).fillna(g['mean_28'])
        frames.append(g)
    return pd.concat(frames, ignore_index=True).dropna(subset=FEATURES)
