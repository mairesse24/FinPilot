from fastapi import APIRouter, Depends

from app.calc.models import FinancialProfile
from app.deps import get_profile
from app.schemas.accounts import AccountOut, AccountsResult

router = APIRouter(prefix="/api", tags=["accounts"])


@router.get("/accounts", response_model=AccountsResult)
def accounts(p: FinancialProfile = Depends(get_profile)):
    return AccountsResult(accounts=[AccountOut(id=a.id, name=a.name, account_type=a.account_type,
                                               balance=a.balance,apr=a.apr,min_payment=a.min_payment,
                                               credit_limit=a.credit_limit) for a in p.accounts])
