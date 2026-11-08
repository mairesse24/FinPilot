"""Origin-only assumptions for the PNC ledger; never reads future cash movements.

Consumption and cash settlement are different targets. This adapter estimates the
checking-paid fraction and recurring signed cash events from observed history.
"""
import pandas as pd
from .data import VARIABLE


def ledger_assumptions(transactions, as_of):
    origin = pd.Timestamp(as_of)
    past = transactions[(transactions.posted_date<=origin)&(transactions.posted_date>origin-pd.Timedelta(days=90))].copy()
    checking = past[past.account_type=='checking']
    variable = past[(past.flow_class=='expense')&past.category.isin(VARIABLE)]
    all_variable = float(variable.amount.sum())
    cash_variable = float(variable.loc[variable.account_type=='checking','amount'].sum())
    ratio = min(1.,max(0.,cash_variable/all_variable)) if all_variable else 1.
    income = checking[(checking.flow_class=='income')&(checking.balance_change>0)]
    # Separate paydays preserve unequal deposits; /3 on a rolling 90-day window
    # incorrectly treats 5, 6 or 7 payments as exactly three calendar months.
    income_schedule = [{'day':int(day),'amount':round(float(g.balance_change.median()),2)}
                       for day,g in income.groupby(income.posted_date.dt.day)]
    fixed = checking[(checking.balance_change<0)&~checking.category.isin(VARIABLE)&(checking.flow_class!='external_transfer')]
    bills = [{'name':str(cat),'day':int(day),'amount':round(float(-g.balance_change.median()),2)}
             for (cat,day),g in fixed.groupby(['category',fixed.posted_date.dt.day])]
    movements = checking[checking.flow_class=='external_transfer'].copy()
    movements['calendar_day'] = movements.posted_date.dt.day.where(~movements.posted_date.dt.is_month_end,31)
    movements['direction'] = movements.balance_change.ge(0)
    recurring = [{'day':int(day),'amount':round(float(g.balance_change.median()),2)}
                 for (day,_),g in movements.groupby(['calendar_day','direction'])
                 if g.posted_date.dt.to_period('M').nunique()>=2]
    return {'income_schedule':income_schedule,'cash_movement_schedule':recurring,
            'monthly_income':sum(x['amount'] for x in income_schedule),
            'bills':bills,'cash_variable_fraction':ratio,
            'monthly_variable_spending':cash_variable/3,
            'monthly_debt_payments':sum(b['amount'] for b in bills if b['name']=='debt_payment'),
            'paydays':[x['day'] for x in income_schedule] or [1,15]}
