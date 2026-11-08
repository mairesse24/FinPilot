from datetime import date, timedelta
from decimal import Decimal

from app.calc.models import (Account, Bill, FinancialProfile, IncomeSource,
                             Transaction, User)

AS_OF = date(2026, 11, 7)
UID = "u-test"


def empty_profile(as_of: date = AS_OF, user_id: str = UID) -> FinancialProfile:
    return FinancialProfile(user=User(user_id, "Test User", "t@example.com"), as_of=as_of)


def make_profile(**overrides) -> FinancialProfile:
    as_of = overrides.pop("as_of", AS_OF)
    D = Decimal
    txs = [Transaction(f"t{i}", "a-chk", D("-20.00"), "groceries", as_of - timedelta(days=i))
           for i in range(0, 60)]
    txs.append(Transaction("t-inc", "a-chk", D("2100.00"), "income", as_of - timedelta(days=3)))
    base = dict(
        user=User(UID, "Test User", "t@example.com"),
        as_of=as_of,
        accounts=[
            Account("a-chk", UID, "Checking", "checking", D("1000.00")),
            Account("a-sav", UID, "Savings", "savings", D("500.00")),
            Account("a-cc", UID, "Card", "credit_card", D("300.00"), min_payment=D("25.00")),
            Account("a-loan", UID, "Loan", "loan", D("2000.00"), min_payment=D("100.00")),
        ],
        transactions=txs,
        bills=[Bill("b1", UID, "Rent", D("800.00"), "rent", "monthly", as_of + timedelta(days=3))],
        income_sources=[IncomeSource("i1", UID, "Pay", D("1400.00"), "biweekly",
                                     as_of + timedelta(days=5))],
    )
    base.update(overrides)
    return FinancialProfile(**base)
