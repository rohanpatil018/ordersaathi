"""
Input validation helpers for extracted OrderLine data.
Called by normalize.py after building lines from LLM or rules output.
"""
from app.schemas import OrderLine


def has_missing_date(line: OrderLine) -> bool:
    """True if no delivery date could be resolved."""
    return not line.delivery_date


def has_zero_quantity(line: OrderLine) -> bool:
    """True if quantity is zero (LLM received no explicit count)."""
    return line.quantity == 0


def collect_flags(line: OrderLine) -> list[str]:
    """Return a list of human-readable flag strings for this line."""
    flags: list[str] = []
    if has_missing_date(line):
        flags.append("No delivery date found")
    if has_zero_quantity(line):
        flags.append("Quantity missing")
    return flags