"""List synthetic customer IDs using the backend-only Nessie key; no writes."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.config import Settings
from app.data.nessie import NessieClient


def main():
    settings = Settings()
    if not settings.nessie_api_key:
        raise SystemExit("Set NESSIE_API_KEY in your root .env first. Never put it in frontend/.env.")
    client = NessieClient(settings.nessie_api_key, settings.nessie_base_url)
    try:
        customers = client.get("/customers")
        if not isinstance(customers, list):
            raise ValueError("Unexpected customer-list response")
        for c in customers:
            print(f"{c['_id']}  {c.get('first_name', '')} {c.get('last_name', '')}")
        if not customers:
            print("No sandbox customers. Create synthetic customers in the Nessie sandbox before selecting one.")
    except ValueError as exc:
        raise SystemExit(str(exc)) from None
    finally:
        client.close()


if __name__ == "__main__":
    main()
