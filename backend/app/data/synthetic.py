"""Deterministic synthetic customers. Tune the demo story in the block below."""
import random
import uuid
from datetime import date, timedelta
from decimal import Decimal as D

from app.calc.metrics import add_months
from app.calc.models import Account, Bill, IncomeSource, Transaction, User
from app.db.repository import SeedDataset

# ---- Tunable demo constants (Alex Rivera) ---------------------------------------------------
DEMO_USER_ID = "00000000-0000-4000-8000-00000000a1e5"
CHECKING = D("2400.00")
SAVINGS = D("600.00")
CARD_BALANCE, CARD_MIN, CARD_LIMIT, CARD_APR = D("420.00"), D("35.00"), D("3000.00"), D("0.2199")
PAY_AMOUNT = D("2100.00")
PAY_IN_DAYS = 11          # next biweekly paycheck
RENT, RENT_IN_DAYS = D("1500.00"), 4
UTILITIES, UTILITIES_IN_DAYS = D("120.00"), 6
SUBSCRIPTION, SUBSCRIPTION_IN_DAYS = D("16.00"), 8
SAFETY_BUFFER = D("500.00")
HISTORY_DAYS = 360
# Variable spend by weekday (Mon=0 .. Sun=6): {category: amount}. Roughly 40/day on average.
WEEKDAY_SPEND = {
    0: {"groceries": 14, "transportation": 6, "dining": 5},
    1: {"groceries": 10, "transportation": 6, "dining": 6},
    2: {"groceries": 16, "transportation": 6, "dining": 8},
    3: {"groceries": 10, "transportation": 6, "dining": 12},
    4: {"groceries": 20, "dining": 24, "entertainment": 14},
    5: {"groceries": 26, "dining": 28, "entertainment": 22, "shopping": 14},
    6: {"groceries": 18, "dining": 20, "entertainment": 8},
}
# ---------------------------------------------------------------------------------------------

_NS = uuid.UUID("5f0c1f4e-3a54-4d1e-9a58-0c6f1b2a7d11")


def _id(*parts) -> str:
    return str(uuid.uuid5(_NS, "|".join(str(p) for p in parts)))


def _history(account_id, user_id, as_of, pay_next, pay_amt, pay_freq_days, bills, spend_for_day):
    """Transactions for HISTORY_DAYS up to as_of. bills: [(category, amount, due_date)] monthly."""
    txs, n = [], 0

    def add(amount, cat, day):
        nonlocal n
        n += 1
        txs.append(Transaction(_id(user_id, "tx", n), account_id, amount, cat, day))

    start = as_of - timedelta(days=HISTORY_DAYS)
    d = pay_next
    while d > as_of:
        d -= timedelta(days=pay_freq_days)
    while d >= start:
        add(pay_amt, "income", d)
        d -= timedelta(days=pay_freq_days)
    for cat, amt, due in bills:
        k = 0
        while True:
            day = add_months(due, -k, day=due.day)
            k += 1
            if day <= as_of:
                if day < start:
                    break
                add(-amt, cat, day)
    day = start
    while day <= as_of:
        for cat, amt in spend_for_day(day):
            add(-D(amt).quantize(D("0.01")), cat, day)
        day += timedelta(days=1)
    return txs


def build_demo_customer(as_of: date) -> SeedDataset:
    uid = DEMO_USER_ID
    chk, sav, card = _id(uid, "chk"), _id(uid, "sav"), _id(uid, "card")
    rent_due = as_of + timedelta(days=RENT_IN_DAYS)
    util_due = as_of + timedelta(days=UTILITIES_IN_DAYS)
    sub_due = as_of + timedelta(days=SUBSCRIPTION_IN_DAYS)
    pay_next = as_of + timedelta(days=PAY_IN_DAYS)
    txs = _history(chk, uid, as_of, pay_next, PAY_AMOUNT, 14,
                   [("rent", RENT, rent_due), ("utilities", UTILITIES, util_due),
                    ("subscriptions", SUBSCRIPTION, sub_due)],
                   lambda day: list(WEEKDAY_SPEND[day.weekday()].items()))
    return SeedDataset(
        users=[User(uid, "Alex Rivera", "alex.rivera@example.com", SAFETY_BUFFER)],
        accounts=[
            Account(chk, uid, "Everyday Checking", "checking", CHECKING),
            Account(sav, uid, "Savings", "savings", SAVINGS),
            Account(card, uid, "Rewards Card", "credit_card", CARD_BALANCE, apr=CARD_APR,
                    min_payment=CARD_MIN, credit_limit=CARD_LIMIT)],
        transactions=txs,
        bills=[Bill(_id(uid, "rent"), uid, "Rent", RENT, "rent", "monthly", rent_due),
               Bill(_id(uid, "util"), uid, "Utilities", UTILITIES, "utilities", "monthly",
                    util_due),
               Bill(_id(uid, "sub"), uid, "Streaming", SUBSCRIPTION, "subscriptions", "monthly",
                    sub_due)],
        income_sources=[IncomeSource(_id(uid, "pay"), uid, "Paycheck", PAY_AMOUNT, "biweekly",
                                     pay_next)])


_NAMES = ["Jordan Lee", "Sam Patel", "Taylor Kim", "Morgan Diaz", "Casey Nguyen",
          "Riley Brooks", "Jamie Flores", "Drew Carter", "Avery Shah", "Quinn Murphy"]
_PAYS = [1400, 1800, 2600, 3200, 4100, 5200]


def build_random_customers(as_of: date, n: int = 2, seed: int = 42) -> SeedDataset:
    rng = random.Random(seed)
    ds = SeedDataset()
    for i in range(n):
        uid = _id("random", seed, i)
        name = _NAMES[i % len(_NAMES)]
        pay = D(_PAYS[i % len(_PAYS)])
        chk, sav = _id(uid, "chk"), _id(uid, "sav")
        rent = (pay * D("0.30")).quantize(D("0.01"))
        rent_due = as_of + timedelta(days=rng.randint(1, 25))
        util_due = as_of + timedelta(days=rng.randint(1, 25))
        pay_next = as_of + timedelta(days=rng.randint(1, 13))
        daily = float(pay) / 14 * rng.uniform(0.25, 0.55)

        def spend(day, daily=daily):
            out = []
            for cat, share in (("groceries", 0.4), ("dining", 0.25), ("transportation", 0.15),
                               ("entertainment", 0.12), ("shopping", 0.08)):
                if rng.random() < 0.8:
                    out.append((cat, daily * share * rng.uniform(0.3, 1.7) / 0.8))
            return out

        ds.users.append(User(uid, name, f"user{i}@example.com", D("500.00")))
        ds.accounts += [
            Account(chk, uid, "Checking", "checking",
                    (pay * D(str(rng.uniform(0.3, 1.5)))).quantize(D("0.01"))),
            Account(sav, uid, "Savings", "savings",
                    (pay * D(str(rng.uniform(0.2, 3.0)))).quantize(D("0.01")))]
        if i % 2 == 0:
            ds.accounts.append(Account(_id(uid, "card"), uid, "Credit Card", "credit_card",
                                       (pay * D("0.4")).quantize(D("0.01")), apr=D("0.2399"),
                                       min_payment=(pay * D("0.03")).quantize(D("0.01")),
                                       credit_limit=D("5000.00")))
        ds.transactions += _history(chk, uid, as_of, pay_next, pay, 14,
                                    [("rent", rent, rent_due), ("utilities", D("95.00"), util_due)],
                                    spend)
        ds.bills += [Bill(_id(uid, "rent"), uid, "Rent", rent, "rent", "monthly", rent_due),
                     Bill(_id(uid, "util"), uid, "Utilities", D("95.00"), "utilities", "monthly",
                          util_due)]
        ds.income_sources.append(IncomeSource(_id(uid, "pay"), uid, "Paycheck", pay, "biweekly",
                                              pay_next))
    return ds
