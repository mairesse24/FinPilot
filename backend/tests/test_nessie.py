from datetime import date
from decimal import Decimal

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.data.nessie import NessieClient, Schedules, import_customer, money
from app.db.memory import InMemoryRepository
from app.main import create_app

AS_OF = date(2026, 11, 7)


def fixture_client(overrides=None):
    responses = {
        '/customers/c1': {'_id': 'c1', 'first_name': 'Synthetic', 'last_name': 'Tester'},
        '/customers/c1/accounts': [
            {'_id': 'a1', 'customer_id': 'c1', 'type': 'Checking', 'balance': 1000},
            {'_id': 'a2', 'customer_id': 'c1', 'type': 'Savings', 'balance': 400},
            {'_id': 'a3', 'customer_id': 'c1', 'type': 'Credit Card', 'balance': 200}],
    }
    for aid in ('a1', 'a2', 'a3'):
        for kind in ('purchases', 'deposits', 'withdrawals', 'loans'):
            responses[f'/accounts/{aid}/{kind}'] = []
    responses['/accounts/a1/purchases'] = [
        {'_id': 'p1', 'payer_id': 'a1', 'purchase_date': '2026-11-06', 'amount': 10.25, 'status': 'completed'},
        {'_id': 'p2', 'payer_id': 'a1', 'purchase_date': '2026-11-06', 'amount': 99, 'status': 'pending'}]
    responses['/accounts/a1/deposits'] = [
        {'_id': 'd1', 'payee_id': 'a1', 'transaction_date': '2026-11-05', 'amount': 100, 'status': 'completed'}]
    responses.update(overrides or {})
    def handle(request):
        assert request.url.params['key'] == 'fake-key'
        assert request.method == 'GET'
        return httpx.Response(200, json=responses[request.url.path])
    return NessieClient('fake-key', client=httpx.Client(transport=httpx.MockTransport(handle)))


def test_nessie_normalization_and_api_horizons():
    ds, warnings = import_customer(fixture_client(), 'c1', AS_OF)
    assert [t.amount for t in ds.transactions] == [Decimal('-10.25'), Decimal('100')]
    assert not ds.income_sources and not ds.bills
    assert any('No confirmed future income' in w for w in warnings)
    repo = InMemoryRepository(ds)
    repo.source, repo.warnings = 'Nessie sandbox', warnings
    app = create_app(repo, Settings(_env_file=None, data_source='nessie', nessie_customer_id='c1',
                                  as_of_date=AS_OF, intelligence_mode='baseline'))
    with TestClient(app) as client:
        dashboard = client.get('/api/dashboard').json()
        assert dashboard['net_worth'] == 1200  # 1000 checking + 400 savings - 200 owed
        assert dashboard['spending_30d'] == 10.25
        assert dashboard['income_30d'] == 100
        assert client.get('/api/context').json()['data_source'] == 'Nessie sandbox'
        assert client.get('/api/dashboard?user_id=another').status_code == 404
        for days in (7, 30, 90):
            response = client.get(f'/api/forecast?days={days}')
            assert response.status_code == 200
            result = response.json()
            assert len(result['series']) == days
            assert result['series'][0]['date'] == '2026-11-08'
            assert all(r['low'] <= r['projected_balance'] <= r['high'] for r in result['series'])


@pytest.mark.parametrize('override', [
    {'/customers/c1': {'_id': 'another'}},
    {'/accounts/a1/purchases': [{'_id': 'p', 'payer_id': 'another', 'purchase_date': '2026-11-06', 'amount': 10, 'status': 'completed'}]},
    {'/customers/c1/accounts': [{'_id': 'a1', 'customer_id': 'another', 'type': 'Checking', 'balance': 100}]},
])
def test_foreign_records_rejected(override):
    with pytest.raises(ValueError):
        import_customer(fixture_client(override), 'c1', AS_OF)


def test_duplicate_transactions_rejected():
    row = {'_id': 'p', 'payer_id': 'a1', 'purchase_date': '2026-11-06', 'amount': 10, 'status': 'completed'}
    with pytest.raises(ValueError, match='Duplicate'):
        import_customer(fixture_client({'/accounts/a1/purchases': [row, row]}), 'c1', AS_OF)


@pytest.mark.parametrize('value', ['NaN', 'Infinity', '-1', '1.001'])
def test_invalid_money_rejected(value):
    with pytest.raises(ValueError):
        money(value)


def test_http_error_does_not_expose_key():
    transport = httpx.MockTransport(lambda request: httpx.Response(403))
    client = NessieClient('secret-key', client=httpx.Client(transport=transport))
    with pytest.raises(ValueError) as error:
        client.get('/customers')
    assert 'secret-key' not in str(error.value)


def test_explicit_schedules_and_fixed_payment_categories():
    schedules = Schedules.model_validate({'customer_id': 'c1',
        'income': [{'name': 'Pay', 'amount': 500, 'frequency': 'biweekly', 'date': '2026-11-08'}],
        'bills': [{'name': 'Rent', 'amount': 200, 'frequency': 'monthly', 'date': '2026-11-09', 'category': 'rent'}],
        'transaction_categories': {'purchases:p1': 'rent'}})
    ds, _ = import_customer(fixture_client(), 'c1', AS_OF, schedules)
    assert ds.transactions[0].category == 'rent'
    assert ds.income_sources[0].amount == 500
    assert ds.bills[0].due_date == date(2026, 11, 9)


def test_explicit_default_category_classifies_seeded_checking_purchases():
    schedules = Schedules.model_validate({
        'customer_id': 'c1', 'default_checking_purchase_category': 'shopping',
    })
    ds, warnings = import_customer(fixture_client(), 'c1', AS_OF, schedules)
    assert ds.transactions[0].category == 'shopping'
    assert not any('Unmapped purchases' in warning for warning in warnings)


def test_overdrawn_checking_is_preserved_not_clamped():
    accounts = [{'_id': 'a1', 'customer_id': 'c1', 'type': 'Checking', 'balance': -100}]
    ds, _ = import_customer(fixture_client({'/customers/c1/accounts': accounts}), 'c1', AS_OF)
    assert ds.accounts[0].balance == Decimal('-100')


def test_live_deposit_shape_uses_verified_account_endpoint():
    row = {'_id': 'd1', 'transaction_date': '2026-11-05', 'amount': 100, 'status': 'completed'}
    ds, _ = import_customer(fixture_client({'/accounts/a1/deposits': [row]}), 'c1', AS_OF)
    assert ds.transactions[-1].account_id == 'a1'
    assert ds.transactions[-1].amount == Decimal('100')
    with pytest.raises(ValueError, match='Foreign'):
        import_customer(fixture_client({'/accounts/a1/deposits': [{**row, 'payee_id': 'another'}]}), 'c1', AS_OF)


def test_loan_uses_confirmed_remaining_principal_not_original_amount():
    loan = {'_id': 'l1', 'status': 'approved', 'amount': 5000, 'monthly_payment': 100, 'type': 'auto'}
    fixture = {'/accounts/a1/loans': [loan]}
    ds, warnings = import_customer(fixture_client(fixture), 'c1', AS_OF)
    assert not any(a.account_type == 'loan' for a in ds.accounts)
    assert any('omitted from net worth' in w for w in warnings)
    schedules = Schedules.model_validate({'customer_id': 'c1', 'loan_balances': {'l1': 500}})
    ds, _ = import_customer(fixture_client(fixture), 'c1', AS_OF, schedules)
    assert ds.accounts[1].account_type == 'loan'
    assert ds.accounts[1].balance == 500
    assert ds.accounts[1].min_payment is None  # scheduled bills own the actual due dates


def test_schedule_liability_link_is_preserved_and_foreign_link_rejected():
    body={'customer_id':'c1','bills':[{'name':'Card payment','amount':35,'frequency':'monthly',
           'date':'2026-11-09','category':'debt_payment','liability_account_id':'a3'}]}
    ds,_=import_customer(fixture_client(),'c1',AS_OF,Schedules.model_validate(body))
    assert ds.bills[0].liability_account_id=='a3'
    body['bills'][0]['liability_account_id']='foreign'
    with pytest.raises(ValueError,match='imported liability'):
        import_customer(fixture_client(),'c1',AS_OF,Schedules.model_validate(body))


def test_refunds_transfers_fixed_bills_and_card_activity_do_not_inflate_variable_spending():
    from app.calc.metrics import checking_variable_transactions,window_inflow
    def purchase(key,account='a1',amount=100):
        return {'_id':key,'payer_id':account,'purchase_date':'2026-11-06','amount':amount,'status':'completed'}
    fixture={'/accounts/a1/purchases':[purchase('rent'),purchase('transfer'),purchase('variable',amount=12)],
             '/accounts/a3/purchases':[purchase('card','a3')],
             '/accounts/a1/withdrawals':[{'_id':'atm','transaction_date':'2026-11-06','amount':50,'status':'completed'}],
             '/accounts/a1/deposits':[{'_id':'refund','transaction_date':'2026-11-06','amount':9,'status':'completed'}]}
    schedules=Schedules.model_validate({'customer_id':'c1','transaction_categories':{
        'purchases:rent':'rent','purchases:transfer':'transfer','deposits:refund':'refund'}})
    ds,warnings=import_customer(fixture_client(fixture),'c1',AS_OF,schedules)
    p=InMemoryRepository(ds).load_profile('c1',AS_OF)
    assert sum(-t.amount for t in checking_variable_transactions(p))==12
    assert window_inflow(p,30)==0 # mapped refund is not salary/income
    assert any('ATM withdrawals excluded' in w for w in warnings)
    assert not any('Checking deposits are shown' in w for w in warnings)
