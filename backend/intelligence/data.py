"""Adapter for the PNC positive-amount ledger (not the smaller signed JSON demo)."""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PNC = ROOT / 'vendor/pnc-utd-hackathon-2026/Lab_Package/data'
VARIABLE = {'groceries', 'transport', 'dining', 'shopping', 'other_spending'}
LIABILITIES = {'credit_card', 'auto_loan', 'personal_loan', 'mortgage'}


def load_daily(path=PNC):
    tx = pd.read_csv(Path(path) / 'transactions.csv', parse_dates=['posted_date'])
    # Only consumption: exclude transfers, debt principal, noncash charges and income.
    spending = tx[(tx.flow_class == 'expense') & tx.category.isin(VARIABLE)]
    pieces = []
    for cid, history in tx.groupby('customer_id'):
        days = pd.date_range(history.posted_date.min(), history.posted_date.max())
        values = spending[spending.customer_id == cid].groupby('posted_date').amount.sum()
        frame = pd.DataFrame({'date': days, 'spending': values.reindex(days, fill_value=0).values})
        frame['customer_id'] = cid
        pieces.append(frame)
    return pd.concat(pieces, ignore_index=True)


def load_customer(customer_id='C001', path=PNC):
    path = Path(path)
    accounts = pd.read_csv(path / 'accounts.csv')
    accounts = accounts[accounts.customer_id == customer_id]
    if accounts.empty:
        raise ValueError('Unknown synthetic customer')
    tx = pd.read_csv(path / 'transactions.csv', parse_dates=['posted_date'])
    tx = tx[tx.customer_id == customer_id]
    as_of = pd.Timestamp(accounts.as_of_date.iloc[0])
    recent = tx[(tx.posted_date > as_of - pd.Timedelta(days=90)) & (tx.posted_date <= as_of)]
    monthly = lambda mask: float(recent.loc[mask, 'amount'].sum() / 3)
    variable = monthly((recent.flow_class == 'expense') & recent.category.isin(VARIABLE))
    # Scheduled housing/utilities and debt are not also forecast as variable spending.
    bills = []
    for category, group in recent[(recent.flow_class == 'expense') & ~recent.category.isin(VARIABLE)].groupby('category'):
        bills.append({'name': category, 'amount': round(float(group.amount.sum()/3), 2),
                      'day': int(group.posted_date.dt.day.mode().iloc[0])})
    debt = float(accounts.loc[accounts.account_type.isin(LIABILITIES), 'monthly_payment'].sum())
    if debt:
        bills.append({'name': 'debt_payments', 'amount': round(debt, 2), 'day': 10})
    income = monthly(recent.flow_class == 'income')
    deposits = recent[recent.flow_class == 'income']
    paydays = sorted(set(int(x) for x in deposits.posted_date.dt.day))
    return {'customer_id': customer_id, 'as_of': as_of.date().isoformat(),
            'checking_balance': float(accounts.loc[accounts.account_type == 'checking', 'balance'].sum()),
            'savings_balance': float(accounts.loc[accounts.account_type == 'savings', 'balance'].sum()),
            'monthly_income': round(income, 2), 'monthly_variable_spending': round(variable, 2),
            'monthly_debt_payments': round(debt, 2), 'bills': bills,
            'paydays': paydays or [1, 15], 'safety_buffer': 500.0,
            'budget': None, 'source': 'PNC synthetic ledger',
            'assumptions': ['Income routed to checking for projection; savings kept separate.',
                            'Monthly bills inferred from last 90 days; backend should supply actual schedules.',
                            'Card purchases modeled as immediate cash outflows; card payments excluded to avoid duplication.',
                            'Other debt payments use snapshot amounts; external calibration transfers excluded.']}
