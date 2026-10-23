import datetime as dt
import os
from pathlib import Path

os.environ["USE_GEMINI"] = "0"                       # tests use the offline rules

from app.aggregate import prep_list
from app.extractor.pipeline import run_extraction

SAMPLE = (Path(__file__).resolve().parent.parent / "data" / "sample_chat.txt").read_text(encoding="utf-8")
REF = dt.date(2026, 10, 23)                           # a Friday


def test_sample_chat():
    res = run_extraction(SAMPLE, REF)
    by = {(l.customer, l.item.lower()): l for l in res.lines}

    asha = by[("Asha", "chocolate cake 1kg")]
    assert asha.quantity == 3 and asha.status == "updated" and asha.payment == "cod"
    assert asha.delivery_date == "2026-10-24" and asha.time_slot == "Evening"

    assert by[("Nisha", "samosa")].quantity == 12
    assert by[("Nisha", "chocolate cake 1kg")].status == "needs_review"
    assert by[("Neha", "cupcakes")].time_slot == "4:00 PM" and by[("Neha", "cupcakes")].payment == "paid"
    assert by[("Karan", "pineapple cake 1kg")].delivery_date == "2026-10-25"

    row = next(r for r in prep_list(res.lines) if r["item"].lower() == "chocolate cake 1kg")
    assert row["total"] == 4