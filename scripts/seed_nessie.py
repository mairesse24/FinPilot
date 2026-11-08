"""Create a fictional demo in the Nessie sandbox, only with --apply.

Resumable local checkpoints prevent duplicate resources on retries. No real bank
connection or transfers. All values are synthetic and intended for API demos.
"""
import argparse
import json
import math
import sys
from datetime import date, timedelta
from pathlib import Path

from dotenv import set_key

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from app.config import Settings
from app.data.nessie import NessieClient

STATE = ROOT / 'data' / 'synthetic' / 'nessie-local.json'
SCHEDULES = ROOT / 'data' / 'synthetic' / 'nessie-schedules-local.json'


DEFAULT_CHECKING_BALANCE = 6500


def seed(settings, configure=False, checking_balance=DEFAULT_CHECKING_BALANCE):
    if not settings.nessie_api_key:
        raise ValueError('Set NESSIE_API_KEY in root .env first')
    if (isinstance(checking_balance, bool) or not isinstance(checking_balance, (int, float))
            or not math.isfinite(checking_balance) or checking_balance < 0):
        raise ValueError('checking_balance must be a finite, nonnegative number')
    state = json.loads(STATE.read_text()) if STATE.exists() else {'created': {}, 'as_of': str(settings.as_of_date or date.today())}
    as_of = date.fromisoformat(state['as_of'])
    client = NessieClient(settings.nessie_api_key, settings.nessie_base_url)
    def create(label, path, body):
        if label in state['created']:
            return state['created'][label]
        try:
            response = client.client.post(client.base_url + path, params={'key': client.key}, json=body)
            if response.status_code not in (200, 201, 202):
                raise ValueError(f'Nessie rejected synthetic resource {label} (HTTP {response.status_code}); no credentials logged')
            payload = response.json()
            result = payload.get('objectCreated', payload)
            result_id = result['_id']
        except (KeyError, json.JSONDecodeError):
            raise ValueError(f'Unexpected creation response for {label}; inspect sandbox before retrying') from None
        state['created'][label] = result_id
        STATE.parent.mkdir(parents=True, exist_ok=True)
        STATE.write_text(json.dumps(state, indent=2))
        print(f'Created synthetic {label}', flush=True)
        return result_id
    try:
        address = {'street_number': '100', 'street_name': 'Demo Lane', 'city': 'Richardson', 'state': 'TX', 'zip': '75080'}
        uid = create('customer', '/customers', {'first_name': 'Alex', 'last_name': 'Rivera', 'address': address})
        checking = create('checking', f'/customers/{uid}/accounts', {'type': 'Checking', 'nickname': 'FinPilot Demo Checking', 'rewards': 0, 'balance': checking_balance})
        abc_checking = create('checking-abc', f'/customers/{uid}/accounts', {'type': 'Checking', 'nickname': 'ABC Bank Checking', 'rewards': 0, 'balance': 5000})
        xyz_checking = create('checking-xyz', f'/customers/{uid}/accounts', {'type': 'Checking', 'nickname': 'XYZ Bank Checking', 'rewards': 0, 'balance': 20000})
        create('savings', f'/customers/{uid}/accounts', {'type': 'Savings', 'nickname': 'Emergency Savings', 'rewards': 0, 'balance': 600})
        create('savings-xyz', f'/customers/{uid}/accounts', {'type': 'Savings', 'nickname': 'XYZ High-Yield Savings', 'rewards': 0, 'balance': 12000})
        create('card', f'/customers/{uid}/accounts', {'type': 'Credit Card', 'nickname': 'Demo Rewards Card', 'rewards': 0, 'balance': 420})
        create('card-travel', f'/customers/{uid}/accounts', {'type': 'Credit Card', 'nickname': 'ABC Travel Card', 'rewards': 0, 'balance': 1850})
        loan = create('loan', f'/accounts/{checking}/loans', {'type': 'auto', 'status': 'approved',
                      'credit_score': 700, 'monthly_payment': 150, 'amount': 5000, 'description': 'Synthetic auto loan'})
        mortgage = create('loan-mortgage', f'/accounts/{xyz_checking}/loans', {'type': 'home', 'status': 'approved',
                          'credit_score': 700, 'monthly_payment': 1450, 'amount': 185000, 'description': 'Synthetic home mortgage'})
        merchant = create('merchant', '/merchants', {'name': 'FinPilot Synthetic Store', 'address': address, 'geocode': {'lat': 32.985, 'lng': -96.75}})
        for i in range(40):
            when = as_of - timedelta(days=119 - i * 3)
            create(f'purchase-{i}', f'/accounts/{checking}/purchases', {
                'merchant_id': merchant, 'medium': 'balance', 'purchase_date': str(when),
                'amount': [38.50, 74.25, 25, 112.80, 46.10][i % 5], 'status': 'completed',
                'description': 'Synthetic discretionary purchase'})
        for i in range(8):
            create(f'payroll-{i}', f'/accounts/{checking}/deposits', {
                'medium': 'balance', 'transaction_date': str(as_of - timedelta(days=1 + i * 14)),
                'amount': 2100, 'status': 'completed', 'description': 'Synthetic biweekly paycheck'})
        schedules = {'customer_id': uid, 'loan_balances': {loan: 5000, mortgage: 185000},
                     'default_checking_purchase_category': 'shopping',
                     'income': [{'name': 'Synthetic biweekly paycheck', 'amount': 2100, 'frequency': 'biweekly', 'date': str(as_of + timedelta(days=11))}],
                     'bills': [{'name': 'Demo rent', 'amount': 1500, 'frequency': 'monthly', 'date': str(as_of + timedelta(days=4)), 'category': 'rent'},
                               {'name': 'Demo utilities', 'amount': 120, 'frequency': 'monthly', 'date': str(as_of + timedelta(days=6)), 'category': 'utilities'},
                               {'name': 'Demo card minimum', 'amount': 35, 'frequency': 'monthly', 'date': str(as_of + timedelta(days=8)), 'category': 'debt_payment'},
                               {'name': 'Demo auto loan payment', 'amount': 150, 'frequency': 'monthly', 'date': str(as_of + timedelta(days=9)), 'category': 'debt_payment', 'liability_account_id': f'loan:{loan}'},
                               {'name': 'Demo mortgage payment', 'amount': 1450, 'frequency': 'monthly', 'date': str(as_of + timedelta(days=12)), 'category': 'debt_payment', 'liability_account_id': f'loan:{mortgage}'}]}
        SCHEDULES.write_text(json.dumps(schedules, indent=2))
        if configure:
            for key, value in {'DATA_SOURCE': 'nessie', 'NESSIE_CUSTOMER_ID': uid,
                               'NESSIE_SCHEDULES_FILE': str(SCHEDULES), 'AS_OF_DATE': str(as_of)}.items():
                set_key(str(ROOT / '.env'), key, value, quote_mode='always')
        print(f'Synthetic Nessie customer: {uid}\nSchedules: {SCHEDULES}')
    finally:
        client.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--configure', action='store_true', help='Select the created customer in root .env')
    parser.add_argument('--checking-balance', type=float, default=DEFAULT_CHECKING_BALANCE,
                        help='Opening checking balance for the fictional customer (default 6500)')
    args = parser.parse_args()
    if not args.apply:
        print('Dry run: creates one fictional customer, 7 bank/card accounts, two loans, 1 merchant, 40 synthetic purchases and 8 historical deposits. Use --apply to create them in Nessie sandbox.')
        return
    try:
        seed(Settings(), args.configure, args.checking_balance)
    except Exception as exc:
        # Network errors contain authenticated request URLs; do not print exception details.
        if isinstance(exc, ValueError):
            raise SystemExit(str(exc)) from None
        raise SystemExit(f'Sandbox seed stopped ({type(exc).__name__}). Local checkpoint retained; no key logged.') from None


if __name__ == '__main__':
    main()
