from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Callable

from app.calc.metrics import bill_occurrences, cash_balance, income_events
from app.calc.models import FinancialProfile


@dataclass
class DayPoint:
    date: date
    balance: Decimal
    spend: Decimal


def project_balance(p: FinancialProfile, days: int,
                    daily_spend: Callable[[date], Decimal]) -> list[DayPoint]:
    income: dict[date, Decimal] = defaultdict(Decimal)
    for d, amt in income_events(p, days):
        income[d] += amt
    bills: dict[date, Decimal] = defaultdict(Decimal)
    for d, b in bill_occurrences(p, days):
        bills[d] += b.amount
    balance = cash_balance(p)
    points = []
    for i in range(1, days + 1):
        day = p.as_of + timedelta(days=i)
        spend = daily_spend(day)
        balance += income[day] - bills[day] - spend
        points.append(DayPoint(day, balance, spend))
    return points
