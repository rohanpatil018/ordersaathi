import datetime as dt
import re
from typing import Optional

from app.schemas import LLMResult, OrderLine

WEEKDAYS = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}
MONTHS = {m: i + 1 for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}
WEEKDAY_RE = r"(mon|tues?|wed(?:nes)?|thu(?:rs?)?|fri|sat(?:ur)?|sun)(?:day)?"


def fmt_num(x: float) -> str:
    return str(int(x)) if float(x).is_integer() else str(x)


def _safe_date(y: int, m: int, d: int) -> Optional[dt.date]:
    try:
        return dt.date(y, m, d)
    except ValueError:
        return None


def resolve_date(phrase: Optional[str], ref: dt.date) -> Optional[dt.date]:
    if not phrase:
        return None
    p = phrase.lower()
    if re.search(r"\bday after tomorrow\b|\bparso\b|\bparson\b", p):
        return ref + dt.timedelta(days=2)
    if re.search(r"\btoday\b|\baaj\b", p):
        return ref
    if re.search(r"\btomorrow\b|\btmrw\b|\btmr\b|\bkal\b", p):
        return ref + dt.timedelta(days=1)

    m = re.search(r"\b(\d{1,2})\s*(?:st|nd|rd|th)?\s*(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b", p)
    day_month = (int(m.group(1)), MONTHS[m.group(2)]) if m else None
    if not day_month:
        m = re.search(r"\b(\d{1,2})[/-](\d{1,2})\b", p)          # dd/mm (Indian order)
        day_month = (int(m.group(1)), int(m.group(2))) if m else None
    if day_month:
        d = _safe_date(ref.year, day_month[1], day_month[0])
        if d and d < ref:
            d = _safe_date(ref.year + 1, day_month[1], day_month[0])
        return d

    m = re.search(rf"\b{WEEKDAY_RE}\b", p)
    if m:
        target = WEEKDAYS[m.group(1)[:3]]
        delta = (target - ref.weekday()) % 7 or 7                # next occurrence
        return ref + dt.timedelta(days=delta)
    return None


def norm_time(*phrases: Optional[str]) -> Optional[str]:
    t = " ".join(p for p in phrases if p).lower()
    m = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", t)
    if m:
        return f"{int(m.group(1))}:{m.group(2) or '00'} {m.group(3).upper()}"
    for words, label in (("morning|subah|savere", "Morning"), ("afternoon|dopahar", "Afternoon"),
                         ("evening|shaam", "Evening"), ("night|raat", "Night")):
        if re.search(rf"\b({words})\b", t):
            return label
    return None


def clean_name(name: str) -> str:
    n = name.lower().strip()
    n = re.sub(r"\bchoco\b", "chocolate", n)
    n = re.sub(r"(\d+(?:\.\d+)?)\s*kg", r"\1kg", n)
    n = re.sub(r"\bcakes\b", "cake", n)
    n = re.sub(r"\bsamosas\b", "samosa", n)
    return re.sub(r"\s+", " ", n)


def build_lines(raw: LLMResult, ref: dt.date) -> list[OrderLine]:
    lines: list[OrderLine] = []
    for order in raw.orders:
        if order.cancelled:
            continue
        d = resolve_date(order.date_phrase, ref)
        slot = norm_time(order.date_phrase, order.time_phrase)
        for it in order.items:
            flags = []
            if it.quantity <= 0:
                flags.append("Quantity missing")
            if d is None:
                flags.append("No delivery date found")
            if it.uncertain:
                flags.append("Customer wasn't sure")
            notes = []
            if it.changed_from:
                notes.append(f"Updated from {it.changed_from} to {fmt_num(it.quantity)}")
            if it.note:
                notes.append(it.note)
            status = "needs_review" if flags else ("updated" if it.changed_from else "confirmed")
            lines.append(OrderLine(
                id=len(lines) + 1,
                customer=order.customer.strip(),
                item=clean_name(it.name).capitalize(),
                quantity=it.quantity,
                delivery_date=d.isoformat() if d else None,
                date_phrase=order.date_phrase,
                time_slot=slot,
                payment=order.payment,
                notes="; ".join(notes) or None,
                status=status,
                flags=flags,
            ))
    return lines