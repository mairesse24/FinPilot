def test_new_routes_are_real_and_legacy_score_is_preserved(client):
    assert client.get('/api/economy').status_code==200
    score=client.get('/api/health').json()['score']
    new=client.get('/api/financial-health').json()
    assert new['version']=='finpilot-financial-health-v2' and new['score'] is None
    assert 0 <= new['observed_score'] <= 100
    assert new['observed_score_basis']=='imported_accounts_transactions_bills_and_income_schedules'
    assert client.get('/api/health').json()['score']==score
    assert client.get('/api/economy?user_id=another').status_code==404
    from app.services.economic_intelligence import _economic_impact
    settings=client.app.state.settings
    profile=client.app.state.repo.load_profile(settings.demo_user_id,settings.as_of_date)
    impact=_economic_impact(profile,{'features':{'PCEPI_yoy_pct':3.0},
        'dimensions':[{'name':'inflation','flagged':True}]})
    assert impact['available'] is True
    assert impact['additional_burn_90d']==round(impact['additional_burn_30d']*3,2)
    assert impact['stress_score']<=impact['baseline_score']
    assert 'not a prediction' in impact['method']


def test_committed_deployment_snapshot_provides_economic_indicators():
    from intelligence.economic_data import cached
    from intelligence.regimes import classify
    snapshot=cached()
    economy=classify(snapshot,snapshot['as_of'])
    assert economy['status']!='Insufficient Data'
    assert economy['features']['CPIAUCSL_yoy_pct'] is not None
    assert economy['features']['PCEPI_yoy_pct'] is not None
    assert all(dimension['available'] for dimension in economy['dimensions'])


def test_scoped_economic_stress_and_facts(client):
    from app.calc.models import Bill
    from decimal import Decimal
    from datetime import timedelta
    settings=client.app.state.settings
    client.app.state.repo._ds.bills.extend([
        Bill('card-due',settings.demo_user_id,'Card due',Decimal(25),'debt_payment','monthly',settings.as_of_date+timedelta(days=4),'a-cc'),
        Bill('loan-due',settings.demo_user_id,'Loan due',Decimal(100),'debt_payment','monthly',settings.as_of_date+timedelta(days=6),'a-loan')])
    body={'facts':{'take_home_income':3000,'essential_cash_expenses':1500,'discretionary_cash_expenses':300,
                   'required_debt_payments':125,'accessible_emergency_savings':300,'debt_complete':True,'bills_complete':True}}
    result=client.post('/api/financial-health/assess',json=body)
    assert result.status_code==200 and 0<=result.json()['score']<=100
    sim=client.post('/api/economic-simulate',json={**body,'scenario':{'type':'emergency_expense','amount':1000}})
    assert sim.status_code==200 and sim.json()['ending_checking_change']==-1000
    assert client.post('/api/economic-simulate',json={**body,'scenario':{'type':'debt_repayment','amount':10,'liability_account_id':'foreign'}}).status_code==422
    assert client.post('/api/financial-health/assess',json={'facts':{'take_home_income':'NaN'}}).status_code==422


def test_chat_automatic_score_and_economic_data_grounded(client):
    r=client.post('/api/chat',json={'messages':[{'role':'user','content':'Why is my health score 72?'}]})
    assert r.status_code==200 and 'Automatic observed-data estimate' in r.json()['reply']
    assert r.json()['tool_calls'][0]['name']=='get_financial_assessment'
    r=client.post('/api/chat',json={'messages':[{'role':'user','content':'How is the economy?'}]})
    assert r.status_code==200 and r.json()['tool_calls'][0]['name']=='get_economic_resilience'
    r=client.post('/api/chat',json={'messages':[{'role':'user','content':'What happens if my expenses rise?'}]})
    assert 'Specify' in r.json()['reply']
    r=client.post('/api/chat',json={'messages':[{'role':'user','content':'Transfer $999999 from checking to savings'}]})
    assert r.status_code==200 and 'unavailable' in r.json()['reply']


def test_assessment_rejection_identifies_the_invalid_savings_field(client):
    r=client.post('/api/resilience',json={'facts':{'take_home_income':7000,
        'essential_cash_expenses':2000,'discretionary_cash_expenses':120,
        'required_debt_payments':1500,'accessible_emergency_savings':2000,
        'bills_complete':True,'debt_complete':True}})
    assert r.status_code==422
    assert 'accessible_emergency_savings' in r.json()['field_errors']
    constraints=client.get('/api/financial-inputs').json()
    assert constraints['savings_balance']==500
    assert client.get('/api/financial-inputs?user_id=another').status_code==404


def test_input_budget_floor_includes_fractional_cent_weekly_obligations(client):
    from app.calc.models import Bill
    from decimal import Decimal
    settings=client.app.state.settings
    client.app.state.repo._ds.bills.append(Bill('weekly-essential',settings.demo_user_id,
        'Weekly essential bill',Decimal(2),'utilities','weekly',settings.as_of_date))
    minimum=client.get('/api/financial-inputs').json()['essential_bill_floor']
    assert minimum==808.58 # 800 rent + 2 * 30/7; 808.57 would be below the actual floor
    assert client.post('/api/resilience',json={'facts':{'essential_cash_expenses':minimum,'bills_complete':True}}).status_code==200


def test_missing_spending_classification_cannot_produce_perfect_automatic_score():
    from app.calc.models import Account,Bill,FinancialProfile,IncomeSource,Transaction,User
    from app.services.economic_intelligence import assessment
    from datetime import date,timedelta
    from decimal import Decimal as D
    as_of=date(2026,11,7);uid='sparse'
    p=FinancialProfile(User(uid,'Sparse','s@example.com'),as_of,
      [Account('c',uid,'Checking','checking',D('6500')),Account('s',uid,'Savings','savings',D('600')),
       Account('cc',uid,'Card','credit_card',D('420'),min_payment=D('35')),
       Account('l',uid,'Loan','loan',D('5000'),min_payment=D('150'))],
      [Transaction('income','c',D('6300'),'income',as_of-timedelta(days=2)),
       Transaction('unknown','c',D('-590'),'other',as_of-timedelta(days=1))],
      [Bill('rent',uid,'Rent',D('1500'),'rent','monthly',as_of+timedelta(days=5)),
       Bill('util',uid,'Utilities',D('120'),'utilities','monthly',as_of+timedelta(days=6)),
       Bill('card',uid,'Card',D('35'),'debt_payment','monthly',as_of+timedelta(days=7),'cc'),
       Bill('loan',uid,'Loan',D('150'),'debt_payment','monthly',as_of+timedelta(days=9),'l')],
      [IncomeSource('pay',uid,'Deposits',D('3150'),'biweekly',as_of+timedelta(days=8))],
      ('Unmapped purchases use category other.',))
    result=assessment(p)
    assert result['observed_score']<100
    assert result['observed_score_confidence']!='high'
    assert any('uncategorized' in x.lower() for x in result['observed_score_limitations'])
