from urllib.parse import quote

from app.aggregate import line_total, pretty_date
from app.extractor.normalize import fmt_num
from app.schemas import OrderLine

ASKS = {
    "No delivery date found": "What date and time should I deliver?",
    "Customer wasn't sure": "Shall I keep this one in your order?",
    "Quantity missing": "How many would you like?",
}


def wa_link(text: str) -> str:
    return "https://wa.me/?text=" + quote(text)       # opens WhatsApp's contact picker


def _desc(l: OrderLine) -> str:
    when = " ".join(x for x in [pretty_date(l.delivery_date) if l.delivery_date else None, l.time_slot] if x)
    return f"• {fmt_num(l.quantity)} × {l.item}" + (f" ({when})" if when else "")


def build_reminders(lines: list[OrderLine], prices: dict) -> list[dict]:
    by_customer: dict[str, list[OrderLine]] = {}
    for l in lines:
        by_customer.setdefault(l.customer, []).append(l)

    out = []
    for customer, ls in by_customer.items():
        review = [l for l in ls if l.status == "needs_review"]
        if review:
            asks = []
            for l in review:
                for f in l.flags:
                    if ASKS.get(f) and ASKS[f] not in asks:
                        asks.append(ASKS[f])
            msg = (f"Hi {customer}! 👋 Quick check before I lock in your order:\n"
                   + "\n".join(_desc(l) for l in review) + "\n" + " ".join(asks) + "\nThank you! 🙏")
            out.append({"customer": customer, "kind": "confirm", "message": msg, "link": wa_link(msg)})
            continue

        pending = [l for l in ls if l.payment in ("online", "unknown")]
        if pending:
            total = sum(line_total(l, prices) for l in pending)
            amount = f"The total is ₹{round(total)}. " if total else ""
            ask = ("Please pay online and send me a screenshot." if all(l.payment == "online" for l in pending)
                   else "Would you like to pay online or on delivery?")
            msg = (f"Hi {customer}! 👋 Your order is confirmed:\n" + "\n".join(_desc(l) for l in pending)
                   + f"\n{amount}{ask} Thank you! 🙏")
            out.append({"customer": customer, "kind": "payment", "message": msg, "link": wa_link(msg)})
    return out