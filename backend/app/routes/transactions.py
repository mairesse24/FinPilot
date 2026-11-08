from datetime import date

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query

from app.calc.models import FinancialProfile
from app.db.repository import Repository
from app.deps import get_profile, get_repo, get_user_id
from app.schemas.accounts import SavingsStressResult, TransactionOut, TransactionsResult

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
