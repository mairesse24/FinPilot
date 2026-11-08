from datetime import date

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query

from app.calc.models import FinancialProfile
from app.db.repository import Repository
from app.deps import get_profile, get_repo, get_user_id
from app.schemas.accounts import (SavingsStressResult, SimulatedTransactionRequest,
                                  SimulatedTransactionResult, TransactionOut,
                                  TransactionsResult)

router = APIRouter(prefix="/api", tags=["transactions"])


@router.get("/transactions", response_model=TransactionsResult)
def transactions(limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0),
                 category: str | None = None,
                 date_from: date | None = Query(None, alias="from"),
                 date_to: date | None = Query(None, alias="to"),
                 uid: str = Depends(get_user_id), repo: Repository = Depends(get_repo)):
    items, total = repo.list_transactions(uid, limit=limit, offset=offset, category=category,
                                          date_from=date_from, date_to=date_to)
    return TransactionsResult(items=[TransactionOut(id=t.id, account_id=t.account_id,
                                                    amount=t.amount, category=t.category,
                                                    date=t.date) for t in items], total=total)


@router.post("/demo/savings-stress", response_model=SavingsStressResult)
def savings_stress_demo(profile: FinancialProfile = Depends(get_profile)):
    """Read-only judge demo: preview a purchase equal to 90% of savings."""
    savings=sum((a.balance for a in profile.accounts if a.account_type=='savings'),Decimal(0))
    if savings<=0:
        raise HTTPException(status_code=422,detail="A savings balance is required for this demo.")
    amount=(savings*Decimal('0.90')).quantize(Decimal('0.01'))
    remaining=savings-amount
    return SavingsStressResult(mode='simulation',executed=False,percentage=90,
        purchase_amount=amount,savings_before=savings,savings_after=remaining,
        alert={'id':'demo-savings-depletion','title':'Large savings purchase simulated','severity':'high',
            'cause':f'A hypothetical ${amount:,.2f} purchase would use 90% of savings and leave ${remaining:,.2f}.',
            'recommended_action':'Review emergency reserves and upcoming bills before making this purchase.'})


@router.post("/demo/transaction", response_model=SimulatedTransactionResult)
def simulate_transaction(req: SimulatedTransactionRequest,
                         profile: FinancialProfile = Depends(get_profile)):
    """Preview a fictional purchase without mutating Nessie or repository data."""
    account = next((a for a in profile.accounts if a.id == req.account_id), None)
    if account is None:
        raise HTTPException(status_code=404, detail="Account is not available in this customer profile.")
    if account.account_type not in {"checking", "savings"}:
        raise HTTPException(status_code=422, detail="Select a checking or savings account for a purchase simulation.")
    liquid = sum((a.balance for a in profile.accounts
                  if a.account_type in {"checking", "savings"}), Decimal(0))
    after = account.balance - req.amount
    liquid_after = liquid - req.amount
    account_share = (req.amount / account.balance * 100) if account.balance > 0 else Decimal(100)
    liquid_share = (req.amount / liquid * 100) if liquid > 0 else Decimal(100)
    alerts = []
    if after < 0:
        alerts.append({'id': 'simulated-insufficient-funds', 'title': 'Insufficient funds warning',
                       'severity': 'critical',
                       'cause': f'The ${req.amount:,.2f} simulation exceeds {account.name}\'s ${account.balance:,.2f} balance by ${-after:,.2f}.',
                       'recommended_action': 'Use a smaller amount or compare another funding account; no transaction was executed.'})
    elif after < profile.user.safety_buffer:
        alerts.append({'id': 'simulated-buffer-breach', 'title': 'Safety buffer warning',
                       'severity': 'high',
                       'cause': f'This simulation leaves ${after:,.2f} in {account.name}, below the ${profile.user.safety_buffer:,.2f} safety buffer.',
                       'recommended_action': 'Review upcoming bills and preserve enough accessible cash before proceeding.'})
    if account.balance > 0 and account_share >= 50:
        alerts.append({'id': 'simulated-large-account-share', 'title': 'Large transaction warning',
                       'severity': 'high',
                       'cause': f'The simulated purchase uses {account_share:.1f}% of {account.name}.',
                       'recommended_action': 'Compare the purchase with upcoming obligations and your emergency reserve.'})
    elif liquid > 0 and liquid_share >= 25:
        alerts.append({'id': 'simulated-large-liquid-share', 'title': 'Large transaction notice',
                       'severity': 'medium',
                       'cause': f'The simulated purchase uses {liquid_share:.1f}% of total checking and savings.',
                       'recommended_action': 'Use the cash-flow forecast to confirm near-term bills remain covered.'})
    return SimulatedTransactionResult(account_id=account.id, account_name=account.name,
        amount=req.amount, balance_before=account.balance, balance_after=after,
        total_liquid_before=liquid, total_liquid_after=liquid_after,
        account_share_percent=round(float(account_share), 2),
        liquid_share_percent=round(float(liquid_share), 2), alerts=alerts)
