"""Small fixed-origin recursive holdout check for all promised forecast horizons."""
import json
import numpy as np
import pandas as pd
from backend.intelligence.data import ROOT, load_daily
from backend.intelligence.forecasting import forecast_spending


def main():
    daily = load_daily()
    rows = []
    for cid in ['C001', 'C002', 'C025', 'C026']:
        customer = daily[daily.customer_id == cid].sort_values('date')
        for offset in (90, 104):
            history, future = customer.iloc[:-offset].copy(), customer.iloc[-offset:][:90]
            prediction = forecast_spending(history, 90)
            pred = np.array([r['spending'] for r in prediction['daily']])
            actual = future.spending.to_numpy()
            mean_baseline = np.repeat(history.spending.iloc[-28:].mean(), 90)
            seasonal = np.resize(history.spending.iloc[-7:].to_numpy(), 90)
            calendar = []
            observed = history.set_index('date').spending.to_dict()
            for day in future.date:
                value = float(observed.get(day-pd.DateOffset(months=1), history.spending.iloc[-28:].mean()))
                calendar.append(value)
                observed[day] = value
            for days in (7, 30, 90):
                errors = actual[:days]-pred[:days]
                active = actual[:days] > 0
                rows.append({'customer_id': cid, 'heldout_customer': cid in ['C025', 'C026'],
                         'origin': str(history.date.max().date()), 'horizon_days': days,
                         'recursive_mae_usd': round(float(np.mean(np.abs(actual[:days]-pred[:days]))), 4),
                         'moving_average_mae_usd': round(float(np.mean(np.abs(actual[:days]-mean_baseline[:days]))), 4),
                         'seasonal_7_mae_usd': round(float(np.mean(np.abs(actual[:days]-seasonal[:days]))), 4),
                         'calendar_month_mae_usd': round(float(np.mean(np.abs(actual[:days]-np.array(calendar[:days])))), 4),
                         'spending_day_mae_usd': round(float(np.mean(np.abs(errors[active]))), 4) if active.any() else None,
                         'total_spending_error_pct': round(float((pred[:days].sum()-actual[:days].sum())/actual[:days].sum()*100), 3) if actual[:days].sum() else None,
                         'total_spending_error_usd': round(float(pred[:days].sum()-actual[:days].sum()), 2)})
    result = {'method': 'Recursive forecasts; 4 synthetic customers, two overlapping test origins each. Overlap means errors are not independent; not comprehensive validation.',
              'results': rows}
    destination = ROOT / 'artifacts/reports/recursive-backtest.json'
    destination.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(pd.DataFrame(rows).to_string(index=False))


if __name__ == '__main__':
    main()
