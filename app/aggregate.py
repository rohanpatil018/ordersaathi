import datetime as dt
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Optional

from app.extractor.normalize import fmt_num
from app.schemas import OrderLine

PRICE_FILE = Path(__file__).resolve().parent.parent / "data" / "price_list.json"


def _key(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def load_prices() -> dict[str, float]:
    try:
        raw = json.loads(PRICE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return {_key(k): v for k, v in raw.items()}


def line_total(l: OrderLine, prices: dict) -> float:
    return prices.get(_key(l.item), 0) * l.quantity


def pretty_date(iso: Optional[str]) -> str:
    return dt.date.fromisoformat(iso).strftime("%a, %d %b") if iso else "Date not set"


def slot_minutes(slot: Optional[str]) -> int:
    if not slot:
        return 24 * 60
    m = re.match(r"(\d{1,2}):(\d{2}) (AM|PM)", slot)
    if m:
        return (int(m.group(1)) % 12 + (12 if m.group(3) == "PM" else 0)) * 60 + int(m.group(2))
    return {"Morning": 540, "Afternoon": 840, "Evening": 1080, "Night": 1260}.get(slot, 24 * 60)


def prep_list(lines: list[OrderLine]) -> list[dict]:
    groups = defaultdict(lambda: {"item": "", "confirmed": 0.0, "review": 0.0})
    for l in lines:
        g = groups[(l.delivery_date or "9999-99-99", _key(l.item))]
        g["item"] = l.item
        g["review" if l.status == "needs_review" else "confirmed"] += l.quantity
    rows = []
    for (d, _), g in sorted(groups.items()):
        total = g["confirmed"] + g["review"]
        label = fmt_num(total)
        if g["review"] and not g["confirmed"]:
            label += " (needs review)"
        elif g["review"]:
            label += f" ({fmt_num(g['confirmed'])} confirmed + {fmt_num(g['review'])} to review)"
        iso = None if d.startswith("9999") else d
        rows.append({"date": iso, "date_label": pretty_date(iso), "item": g["item"],
                     "total": total, "label": label})
    return rows


def delivery_sheet(lines: list[OrderLine], prices: dict) -> list[dict]:
    ordered = sorted(lines, key=lambda l: (l.delivery_date or "9999", slot_minutes(l.time_slot), l.customer))
    return [{"date_label": pretty_date(l.delivery_date), "slot": l.time_slot or "Any time",
             "customer": l.customer, "item": l.item, "quantity": l.quantity,
             "payment": l.payment, "status": l.status, "amount": round(line_total(l, prices))}
            for l in ordered]


def summary(lines: list[OrderLine], prices: dict) -> dict:
    return {
        "customers": len({l.customer for l in lines}),
        "items": len(lines),
        "needs_review": sum(1 for l in lines if l.status == "needs_review"),
        "total_amount": round(sum(line_total(l, prices) for l in lines)),
        "to_collect": round(sum(line_total(l, prices) for l in lines if l.payment != "paid")),
        "unpriced_items": sorted({l.item for l in lines if _key(l.item) not in prices}),
    }