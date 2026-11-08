from datetime import date

from fastapi import APIRouter, Depends, Query

from app.db.repository import Repository
from app.deps import get_repo, get_user_id
from app.schemas.accounts import TransactionOut, TransactionsResult

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
