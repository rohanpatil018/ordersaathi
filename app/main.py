import datetime as dt
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

load_dotenv()

from app.aggregate import delivery_sheet, load_prices, prep_list, summary  # noqa: E402
from app.extractor.pipeline import run_extraction  # noqa: E402
from app.messages import build_reminders  # noqa: E402
from app.schemas import ExtractRequest, ExtractResponse, PlanRequest  # noqa: E402

BASE = Path(__file__).resolve().parent.parent
MAX_CHARS = 5000

app = FastAPI(title="OrderSaathi")


@app.get("/api/sample")
def sample():
    return {"chat_text": (BASE / "data" / "sample_chat.txt").read_text(encoding="utf-8")}


@app.post("/api/extract", response_model=ExtractResponse)
def extract(req: ExtractRequest):
    if not req.chat_text.strip():
        raise HTTPException(400, "Paste a chat first.")
    if len(req.chat_text) > MAX_CHARS:
        raise HTTPException(413, f"Chat too long (max {MAX_CHARS} characters).")
    try:
        ref = dt.date.fromisoformat(req.reference_date) if req.reference_date else dt.date.today()
    except ValueError:
        raise HTTPException(400, "reference_date must look like 2026-10-23.")
    return run_extraction(req.chat_text, ref, req.seller_name)


@app.post("/api/plan")
def plan(req: PlanRequest):
    prices = load_prices()
    return {
        "summary": summary(req.lines, prices),
        "prep_list": prep_list(req.lines),
        "delivery_sheet": delivery_sheet(req.lines, prices),
        "reminders": build_reminders(req.lines, prices),
    }


app.mount("/", StaticFiles(directory=BASE / "static", html=True), name="static")