"""Payment status normalization across transaction sources."""

from __future__ import annotations

import pandas as pd

STATUSES = ("Paid", "Pending", "Refunded", "Unknown")


def _canonical(raw: str) -> str:
    s = str(raw or "").strip().lower()
    if s in ("paid", "pay", "complete", "completed", "done"):
        return "Paid"
    if s in ("pending", "outstanding", "unpaid", "due", "todo"):
        return "Pending"
    if s in ("refund", "refunded", "return", "returned", "credit"):
        return "Refunded"
    return "Unknown"


def normalize_payment_status(row: pd.Series) -> str:
    src = str(row.get("source", "")).lower()
    raw = row.get("status_raw", row.get("status", ""))

    if pd.notna(raw) and str(raw).strip():
        return _canonical(str(raw))

    if src == "invoice":
        return "Unknown"

    if src == "note":
        note_type = str(row.get("note_type", "")).lower()
        merchant = str(row.get("merchant_raw", "")).lower()
        if "refund" in note_type or "refund" in merchant:
            return "Refunded"
        if note_type == "todo":
            return "Pending"
        if note_type in ("done", "revenue"):
            return "Paid"
        amt = row.get("amount")
        if amt is not None and not pd.isna(amt) and float(amt) > 0 and "refund" in merchant:
            return "Refunded"
        return "Unknown"

    if src == "statement":
        merchant = str(row.get("merchant_raw", "")).lower()
        amt = row.get("amount")
        if "refund" in merchant or "credit" in merchant:
            return "Refunded"
        if amt is not None and not pd.isna(amt):
            try:
                if float(amt) > 0:
                    return "Paid"
            except (TypeError, ValueError):
                pass
        return "Unknown"

    if src == "receipt":
        return "Paid"

    return "Unknown"
