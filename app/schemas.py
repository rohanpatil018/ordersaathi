from typing import Literal, Optional
from pydantic import BaseModel, Field


# ---------- What Gemini returns (raw facts only) ----------
class LLMItem(BaseModel):
    name: str
    quantity: float
    changed_from: Optional[str]
    uncertain: bool
    note: Optional[str]


class LLMOrder(BaseModel):
    customer: str
    items: list[LLMItem]
    date_phrase: Optional[str]
    time_phrase: Optional[str]
    payment: Literal["cod", "paid", "online", "unknown"]
    cancelled: bool


class LLMResult(BaseModel):
    orders: list[LLMOrder]


# ---------- What the app and UI use (one row per item) ----------
class OrderLine(BaseModel):
    id: int = 0
    customer: str
    item: str
    quantity: float
    delivery_date: Optional[str] = None      # ISO, e.g. "2026-10-24"
    date_phrase: Optional[str] = None
    time_slot: Optional[str] = None
    payment: Literal["cod", "paid", "online", "unknown"] = "unknown"
    notes: Optional[str] = None
    status: Literal["confirmed", "updated", "needs_review"] = "confirmed"
    flags: list[str] = Field(default_factory=list)


class ExtractRequest(BaseModel):
    chat_text: str
    reference_date: Optional[str] = None     # the day the chat happened (ISO)
    seller_name: Optional[str] = None


class ExtractResponse(BaseModel):
    lines: list[OrderLine]
    engine: str                              # "gemini" or "rules"
    warning: Optional[str] = None
    reference_date: str


class PlanRequest(BaseModel):
    lines: list[OrderLine]