"""Train quantile LightGBM; reserve later dates and completely unseen customers."""
import argparse
import json
from pathlib import Path
import lightgbm as lgb
import numpy as np
from sklearn.metrics import mean_absolute_error
from .data import ROOT, load_daily
from .features import FEATURES, make_features

MODEL_DIR = ROOT / 'artifacts/models'


def train(output=MODEL_DIR):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    frame = make_features(load_daily())
    customers = sorted(frame.customer_id.unique())
    heldout = customers[-6:]
    known = ~frame.customer_id.isin(heldout)
    dates = sorted(frame.date.unique())
    train_end, val_end = dates[int(len(dates)*.70)], dates[int(len(dates)*.85)]
    train_mask = known & (frame.date < train_end)
    val_mask = known & (frame.date >= train_end) & (frame.date < val_end)
    test_mask = known & (frame.date >= val_end)
    models = {}
    for name, alpha in [('lower', .1), ('median', .5), ('upper', .9)]:
        model = lgb.LGBMRegressor(objective='quantile', alpha=alpha, n_estimators=400,
                                  learning_rate=.04, num_leaves=23, min_child_samples=40,
                                  random_state=42, n_jobs=2, verbosity=-1)
        model.fit(frame.loc[train_mask, FEATURES], frame.loc[train_mask, 'spending'],
                  eval_set=[(frame.loc[val_mask, FEATURES], frame.loc[val_mask, 'spending'])],
                  callbacks=[lgb.early_stopping(35, verbose=False)])
        model.booster_.save_model(str(output / f'{name}.txt'))
        models[name] = model

    def evaluate(mask):
        f = frame.loc[mask]
        preds = np.sort(np.maximum(0, np.array([models[k].predict(f[FEATURES]) for k in models])), axis=0)
        y = f.spending.to_numpy()
        return {'rows': len(f), 'lightgbm_mae_usd': round(mean_absolute_error(y, preds[1]), 4),
                'moving_average_28_mae_usd': round(mean_absolute_error(y, f.mean_28), 4),
                'seasonal_7_mae_usd': round(mean_absolute_error(y, f.lag_7), 4),
                'calendar_month_mae_usd': round(mean_absolute_error(y, f.calendar_lag_1), 4),
                'interval_coverage_80': float(np.mean((y >= preds[0]) & (y <= preds[2]))),
                'mean_interval_width_usd': float(np.mean(preds[2]-preds[0]))}

    validation = evaluate(val_mask)
    zero_rates = frame.loc[train_mask].groupby('customer_id').spending.apply(lambda s: float((s == 0).mean()))
    # Choose the serving point forecast on validation only, never on the test period.
    candidates = {'lightgbm': validation['lightgbm_mae_usd'],
                  'moving_average_28': validation['moving_average_28_mae_usd'],
                  'seasonal_7': validation['seasonal_7_mae_usd'],
                  'calendar_month': validation['calendar_month_mae_usd']}
    report = {'seed': 42, 'data': 'PNC synthetic ledger; not real customer performance',
              'target': 'daily variable consumption USD', 'features': FEATURES,
              'training_history_profile': {'zero_day_fraction_min': float(zero_rates.min()),
                  'zero_day_fraction_max': float(zero_rates.max()),
                  'fallback_margin': .15, 'note': 'Heuristic support check, not a validated distribution-shift detector.'},
              'train_end_exclusive': str(train_end), 'validation_end_exclusive': str(val_end),
              'heldout_customers': heldout, 'training_rows': int(train_mask.sum()),
              'serving_model': min(candidates, key=candidates.get), 'validation': validation,
              'test': evaluate(test_mask),
              'heldout_customer_test': evaluate(~known & (frame.date >= val_end)),
              'limitations': ['One-day walk-forward metrics use observed prior days.',
                             'Recursive 7/30/90-day accuracy is not established by these metrics.',
                             'Quantiles are empirical, uncalibrated, and not guarantees.',
                             'Synthetic posting patterns may make accuracy unrealistically high.']}
    reports = ROOT / 'artifacts/reports'
    reports.mkdir(parents=True, exist_ok=True)
    (reports / 'training.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    (output / 'metadata.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=MODEL_DIR)
    train(parser.parse_args().output)
