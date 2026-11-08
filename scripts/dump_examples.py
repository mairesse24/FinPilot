"""Dump real baseline responses for the demo customer to docs/examples/. Run from repo root:
   backend/.venv/bin/python scripts/dump_examples.py"""
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from fastapi.testclient import TestClient  # noqa: E402

from app.config import Settings  # noqa: E402
from app.data.synthetic import DEMO_USER_ID, build_demo_customer  # noqa: E402
from app.db.memory import InMemoryRepository  # noqa: E402
from app.main import create_app  # noqa: E402

AS_OF = date(2026, 11, 7)
OUT = ROOT / "docs" / "examples"


def write(name, data):
    (OUT / f"{name}.json").write_text(json.dumps(data, indent=2) + "\n")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    s = Settings(_env_file=None, database_url=None, demo_user_id=DEMO_USER_ID,
                 intelligence_mode="baseline", as_of_date=AS_OF)
    c = TestClient(create_app(repo=InMemoryRepository(build_demo_customer(AS_OF)), settings=s))

    def get(path, **params):
        r = c.get(path, params=params)
        r.raise_for_status()
        return r.json()

    write("dashboard", get("/api/dashboard"))
    write("accounts", get("/api/accounts"))
    write("transactions", get("/api/transactions", limit=10))
    write("health", get("/api/health"))
    write("forecast", get("/api/forecast", days=30))
    g = get("/api/guardian")
    write("guardian", g)
    alert = next(a for a in g["alerts"] if a.get("suggested_scenario"))
    req = {"scenario": {**alert["suggested_scenario"], "reduction_amount": 200}}
    write("simulate_request", req)
    r = c.post("/api/simulate", json=req)
    r.raise_for_status()
    write("simulate_response", r.json())
    creq = {"messages": [{"role": "user", "content": "what can I do?"}]}
    write("chat_request", creq)
    r = c.post("/api/chat", json=creq)
    r.raise_for_status()
    write("chat_response", r.json())
    print("wrote", sorted(p.name for p in OUT.glob("*.json")))


main()
