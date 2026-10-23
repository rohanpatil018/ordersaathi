import datetime as dt
import json
import sys
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if _stream and _stream.encoding and _stream.encoding.lower() != "utf-8":
        _stream.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

load_dotenv()

from app.aggregate import delivery_sheet, load_prices, prep_list, summary
from app.extractor.pipeline import run_extraction
from app.messages import build_reminders
from app.schemas import ExtractRequest, ExtractResponse, PlanRequest

BASE = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE / "static"
MAX_CHARS = 15000

app = FastAPI(title="OrderSaathi")


@app.get("/health")
def health():
    """Used by Render's health check."""
    return {"status": "ok"}


@app.get("/api/sample")
def sample():
    sample_path = BASE / "data" / "sample_chat.txt"
    if not sample_path.exists():
        raise HTTPException(404, "Sample chat file not found.")
    return {"chat_text": sample_path.read_text(encoding="utf-8")}


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
    result = {
        "summary": summary(req.lines, prices),
        "prep_list": prep_list(req.lines),
        "delivery_sheet": delivery_sheet(req.lines, prices),
        "reminders": build_reminders(req.lines, prices),
    }
    # ensure_ascii=False keeps emoji and the rupee sign intact
    return JSONResponse(content=json.loads(json.dumps(result, ensure_ascii=False)))


# The static mount must stay LAST, otherwise it swallows the /api routes (405 errors).
STATIC_DIR.mkdir(exist_ok=True)
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")