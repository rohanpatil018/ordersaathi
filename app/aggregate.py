import datetime as dt
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Optional

from app.extractor.normalize import fmt_num
from app.schemas import OrderLine

PRICE_FILE = Path(__file__).resolve().parent.parent / "data" / "price_list.json"
STOP_WORDS = {"of", "the", "a", "an"}


def _singular(w: str) -> str:
    if len(w) > 4 and w.endswith("ies"):
        return w[:-3] + "y"          # brownies -> browny, cookies -> cooky (same on both sides)
    if len(w) > 4 and w.endswith("xes"):
        return w[:-2]                # boxes -> box
    if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
        return w[:-1]                # cakes -> cake
    return w


def _key(name: str) -> str:
    """Normalise an item name: 'Choco Cakes 1 kg' -> 'chocolate cake 1kg'."""
    s = str(name or "").lower()
    s = re.sub(r"\bchoco\b", "chocolate", s)
    s = re.sub(r"(\d+(?:\.\d+)?)\s*(?:kilograms?|kilos?|kgs?)\b", r"\1kg", s)
    s = re.sub(r"(\d+)\s*(?:grams?|gms?|gm|g)\b", r"\1g", s)
    words = [_singular(w) for w in re.findall(r"[a-z0-9]+", s) if w not in STOP_WORDS]
    return " ".join(words)


class PriceBook(dict):
    """dict of normalised item name -> price, with tolerant lookups."""

    def _resolve(self, key: str):
        if dict.__contains__(self, key):
            return key
        tokens = set(key.split())
        if not tokens:
            return None
        best, best_score = None, 0.0
        for k in dict.keys(self):
            kt = set(k.split())
            if kt <= tokens:                      # price name fully inside the item name
                score = 100 + len(kt)
            elif tokens <= kt:                    # item is a shorter form of the price name
                score = 50 + len(tokens) - 0.1 * len(kt - tokens) + (0.5 if "1kg" in kt else 0)
            else:
                continue
            if score > best_score:
                best, best_score = k, score
        return best

    def __contains__(self, key):
        return self._resolve(key) is not None

    def __getitem__(self, key):
        r = self._resolve(key)
        if r is None:
            raise KeyError(key)
        return dict.__getitem__(self, r)

    def get(self, key, default=None):
        r = self._resolve(key)
        return default if r is None else dict.__getitem__(self, r)


def load_prices() -> dict:
    try:
        raw = json.loads(PRICE_FILE.read_text(encoding="utf-8-sig"))
    except Exception:
        return PriceBook()
    return PriceBook({_key(k): v for k, v in raw.items()})


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