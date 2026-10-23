import datetime as dt
import os
from typing import Optional

from app.extractor.llm import extract_with_gemini
from app.extractor.normalize import build_lines
from app.extractor.rules import extract_with_rules
from app.schemas import ExtractResponse


def run_extraction(chat_text: str, ref_date: dt.date, seller_name: Optional[str] = None) -> ExtractResponse:
    engine, warning, raw = "gemini", None, None

    if os.getenv("USE_GEMINI", "1") == "0":
        engine, warning = "rules", "Offline mode: Gemini is turned off."
    else:
        try:
            raw = extract_with_gemini(chat_text, seller_name)
            if not raw.orders:
                raise ValueError("Gemini returned no orders")
        except Exception as e:
            engine, warning = "rules", f"Gemini unavailable ({type(e).__name__}); used offline rules instead."
            raw = None

    if raw is None:
        raw = extract_with_rules(chat_text, seller_name)

    return ExtractResponse(lines=build_lines(raw, ref_date), engine=engine,
                           warning=warning, reference_date=ref_date.isoformat())