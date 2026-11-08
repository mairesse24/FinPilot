def test_new_routes_are_real_and_legacy_score_is_preserved(client):
    assert client.get('/api/economy').status_code==200
    score=client.get('/api/health').json()['score']
    new=client.get('/api/financial-health').json()
    assert new['version']=='finpilot-financial-health-v2' and new['score'] is None
    assert client.get('/api/health').json()['score']==score
    assert client.get('/api/economy?user_id=another').status_code==404


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


def test_chat_new_score_withheld_and_economic_data_grounded(client):
    r=client.post('/api/chat',json={'messages':[{'role':'user','content':'Why is my health score 72?'}]})
    assert r.status_code==200 and 'withheld' in r.json()['reply']
    assert r.json()['tool_calls'][0]['name']=='get_financial_assessment'
    r=client.post('/api/chat',json={'messages':[{'role':'user','content':'How is the economy?'}]})
    assert r.status_code==200 and r.json()['tool_calls'][0]['name']=='get_economic_resilience'
    r=client.post('/api/chat',json={'messages':[{'role':'user','content':'What happens if my expenses rise?'}]})
    assert 'Specify' in r.json()['reply']
    r=client.post('/api/chat',json={'messages':[{'role':'user','content':'Transfer $999999 from checking to savings'}]})
    assert r.status_code==200 and 'unavailable' in r.json()['reply']
