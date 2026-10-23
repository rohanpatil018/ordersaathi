import re
from typing import Optional

from app.extractor.normalize import fmt_num
from app.schemas import LLMItem, LLMOrder, LLMResult

HEADER_RE = re.compile(
    r"^\[?(?:\d{1,2}/\d{1,2}/\d{2,4},?\s*)?(\d{1,2}:\d{2})(?::\d{2})?\s*(?:[ap]m)?\]?\s*-?\s*([^:\[\]]{1,40}?):\s*(.*)$",
    re.I)

ITEM_RE = re.compile(
    r"(?P<qty>\d+(?:\.\d+)?)\s*(?P<size>kg|boxes|box|dozen)?\s*(?:of\s+)?"
    r"(?P<name>(?:(?:choco(?:late)?|pineapple|vanilla|butterscotch|red velvet|black forest|strawberry|mango)\s+)?"
    r"(?:cakes?|cupcakes?|samosas?|cookies?|brownies?|ladoo|laddu|pastr(?:y|ies)|rolls?))",
    re.I)

DATE_RE = re.compile(
    r"\b(day after tomorrow|parso|tomorrow|tmrw|today|aaj|kal|"
    r"(?:mon|tues?|wed(?:nes)?|thu(?:rs?)?|fri|sat(?:ur)?|sun)(?:day)?)\b", re.I)
TIME_RE = re.compile(r"\b\d{1,2}(?::\d{2})?\s*(?:am|pm)\b", re.I)
DAYPART_RE = re.compile(r"\b(morning|subah|afternoon|dopahar|evening|shaam|night|raat)\b", re.I)
UNCERTAIN_RE = re.compile(r"\b(if possible|if you can|maybe|not sure|will confirm|let you know)\b", re.I)
ACTUALLY_RE = re.compile(
    r"actually\s+(?:make\s+it\s+|it'?s\s+|change\s+to\s+|only\s+)?(\d+(?:\.\d+)?)"
    r"(?:\s+[a-z]+)?(?:\s*,?\s*not\s+\d+(?:\.\d+)?)?", re.I)


def parse_messages(text: str) -> list[list[str]]:
    msgs: list[list[str]] = []
    for raw in text.splitlines():
        line = raw.strip().replace("\u200e", "")
        if not line:
            continue
        m = HEADER_RE.match(line)
        if m:
            msgs.append([m.group(2).strip(), m.group(3).strip()])
        elif msgs:
            msgs[-1][1] += " " + line          # continuation of a multi-line message
    return msgs


def detect_payment(text: str) -> str:
    t = text.lower()
    if re.search(r"\bcod\b|c\.o\.d|cash on delivery|(?:pay|payment)(?: on| after| at) delivery", t):
        return "cod"
    if re.search(r"\bpaid\b|advance (?:paid|done|sent)", t):
        return "paid"
    if re.search(r"\bonline\b|\bupi\b|gpay|google pay|phonepe|paytm|transfer", t):
        return "online"
    return "unknown"


def items_in(sentence: str) -> list[tuple[str, float]]:
    out = []
    for m in ITEM_RE.finditer(sentence):
        qty = float(m.group("qty"))
        size = (m.group("size") or "").lower()
        name = m.group("name").lower()
        if size == "kg":
            name, qty = f"{name} {fmt_num(qty)}kg", 1.0
        elif size in ("box", "boxes"):
            name += " (box)"
        elif size == "dozen":
            name += " (dozen)"
        elif re.search(r"\bcakes?\b", name):
            kg = re.search(r"(\d+(?:\.\d+)?)\s*kg", sentence, re.I)   # '2 cakes 1kg each'
            if kg:
                name += f" {kg.group(1)}kg"
        out.append((name, qty))
    return out


def extract_with_rules(chat_text: str, seller_name: Optional[str] = None) -> LLMResult:
    sellers = {"you", "me"} | ({seller_name.strip().lower()} if seller_name else set())
    orders: list[LLMOrder] = []
    last_order: dict[str, LLMOrder] = {}
    last_item: dict[str, LLMItem] = {}

    for sender, text in parse_messages(chat_text):
        if sender.lower() in sellers:
            continue
        new_items: list[LLMItem] = []

        for sentence in re.split(r"[.!?]+(?!\d)|\n", text):
            s = sentence.strip()
            if not s:
                continue
            uncertain = bool(UNCERTAIN_RE.search(s))
            clause = ACTUALLY_RE.search(s)
            rest = s if not clause else s[:clause.start()] + " " + s[clause.end():]
            found = [LLMItem(name=n, quantity=q, changed_from=None, uncertain=uncertain, note=None)
                     for n, q in items_in(rest)]
            if clause:                                   # a correction like "actually 12"
                n_before = len(items_in(s[:clause.start()]))
                target = found[n_before - 1] if n_before else last_item.get(sender)
                if target is not None:
                    target.changed_from = target.changed_from or fmt_num(target.quantity)
                    target.quantity = float(clause.group(1))
            new_items.extend(found)

        date_m = DATE_RE.search(text)
        time_m = TIME_RE.search(text) or DAYPART_RE.search(text)
        pay = detect_payment(text)

        if new_items:
            order = LLMOrder(customer=sender, items=new_items,
                             date_phrase=date_m.group(0) if date_m else None,
                             time_phrase=time_m.group(0) if time_m else None,
                             payment=pay, cancelled=False)
            orders.append(order)
            last_order[sender] = order
            last_item[sender] = new_items[-1]
        elif sender in last_order:                       # follow-up message with no new item
            o = last_order[sender]
            if re.search(r"\bcancel", text, re.I):
                o.cancelled = True
            if o.payment == "unknown" and pay != "unknown":
                o.payment = pay
            if not o.date_phrase and date_m:
                o.date_phrase = date_m.group(0)
            if not o.time_phrase and time_m:
                o.time_phrase = time_m.group(0)

    return LLMResult(orders=orders)