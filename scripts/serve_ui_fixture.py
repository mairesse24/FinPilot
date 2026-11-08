"""Local-only UI verification server. No .env credentials or banking API requests.

Run: python -m scripts.serve_ui_fixture
All account balances and schedules below are explicitly fictional test inputs.
"""
import os
import sys
from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
os.environ['COPILOT_PROVIDER']='offline'

from app.config import Settings
import app.config as config
from app.data.synthetic import build_demo_customer,DEMO_USER_ID
from app.calc.models import Account,Bill
from app.db.memory import InMemoryRepository

settings=Settings(_env_file=None,data_source='demo',database_url=None,
                  intelligence_mode='auto',as_of_date=date(2026,11,7),demo_user_id=DEMO_USER_ID)
# app.main constructs its default app at import time. Bind the explicit offline
# configuration first, so importing it cannot consult a private .env repository.
config.get_settings=lambda:settings
from app.main import create_app

ds=build_demo_customer(settings.as_of_date)
ds.accounts=[replace(a,balance=Decimal('6500')) if a.account_type=='checking' else a for a in ds.accounts]
ds.accounts.append(Account('fixture-loan',DEMO_USER_ID,'Fictional vehicle loan','loan',Decimal('5000')))
card=next(a for a in ds.accounts if a.account_type=='credit_card')
ds.bills.extend([
    Bill('fixture-card-due',DEMO_USER_ID,'Card payment',Decimal('35'),'debt_payment','monthly',settings.as_of_date+timedelta(days=7),card.id),
    Bill('fixture-loan-due',DEMO_USER_ID,'Vehicle payment',Decimal('150'),'debt_payment','monthly',settings.as_of_date+timedelta(days=9),'fixture-loan')])
app=create_app(repo=InMemoryRepository(ds),settings=settings)

if __name__=='__main__':
    import uvicorn
    uvicorn.run(app,host='127.0.0.1',port=int(os.getenv('UI_FIXTURE_PORT','8001')))
