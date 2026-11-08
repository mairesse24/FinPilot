"""Conservative extraction of explicit purchase facts shared by both Copilot paths."""
import re


def explicit_purchase_args(text: str) -> dict | None:
    normalized = re.sub(r"\b(car|vehicle|house|home|tv)worth\b", r"\1 worth", text.lower())
    item_match = re.search(r"\b(car|vehicle|house|home|tv)\b", normalized)
    if not item_match or not re.search(r"\b(buy|purchase|afford|worth|cost|costs|price)\b", normalized):
        return None
    money = list(re.finditer(r"(?:\$\s*)?(\d[\d,]*(?:\.\d+)?)\s*(?:dollars?|usd)?", normalized))
    values = [float(match.group(1).replace(",", "")) for match in money]
    values = [value for value in values if value > 0]
    if not values:
        return None
    gift_match = re.search(
        r"(?:friend|family|someone).{0,30}?\b(?:give|gift|contribute|contribution)\w*.{0,15}?"
        r"(?:\$\s*)?(\d[\d,]*(?:\.\d+)?)\s*(?:dollars?|usd)?",
        normalized,
    )
    gift = float(gift_match.group(1).replace(",", "")) if gift_match else 0.0
    price_candidates = [value for value in values if value != gift]
    price = max(price_candidates or values)
    raw_item = item_match.group(1)
    item = "car" if raw_item == "vehicle" else "home" if raw_item in ("house", "home") else raw_item
    args = {"amount": price, "item": item}
    if gift:
        args["gift_amount"] = gift
    if "saving" in normalized:
        args["funding_source"] = "savings"
    down = (re.search(r"(?:put|pay)\s*(?:\$\s*)?(\d[\d,]*(?:\.\d+)?)\s*(?:dollars?\s*)?down", normalized)
            or re.search(r"down payment(?:\s+of|\s+is)?\s*(?:\$\s*)?(\d[\d,]*(?:\.\d+)?)", normalized))
    apr = re.search(r"(?:apr|interest rate)(?:\s+is|\s+of)?\s*(\d+(?:\.\d+)?)\s*%", normalized)
    term = re.search(r"(?:term\s+is\s+)?(\d+)\s*(?:months?|month loan)", normalized)
    if down and apr and term:
        args.update(
            down_payment=float(down.group(1).replace(",", "")),
            apr_percent=float(apr.group(1)),
            term_months=int(term.group(1)),
        )
    return args
