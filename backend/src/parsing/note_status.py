"""Payment status inference for parsed note rows (Groq with regex fallback)."""

from __future__ import annotations

import json

from src.cleaning.status import STATUSES
from src.llm.groq_client import groq_available, groq_chat_json

_VALID = frozenset(STATUSES)

_STATUS_SYSTEM = f"""You infer payment status for informal bookkeeping note lines.
Return JSON: {{"results": [{{"id": 0, "status": "Paid"}}, ...]}}
Each status must be exactly one of: {", ".join(STATUSES)}.

Guidelines:
- [todo] or language about unpaid/outstanding/follow up → Pending
- refund, returned, credit came through → Refunded
- paid, sent and paid, completed → Paid
- unclear or non-payment notes → Unknown
"""


def _sanitize_status(val: str) -> str:
    s = str(val or "").strip().title()
    if s in _VALID:
        return s
    return "Unknown"


def _status_fallback(note_type: str, note_text: str) -> str:
    tag = (note_type or "").lower()
    low = (note_text or "").lower()
    if tag == "todo":
        return "Pending"
    if "refund" in low:
        return "Refunded"
    if "paid" in low or "sent and paid" in low:
        return "Paid"
    if "outstanding" in low or "hasn't paid" in low or "unpaid" in low or "hasnt paid" in low:
        return "Pending"
    if tag in ("done", "revenue"):
        return "Paid"
    return "Unknown"


def _groq_status_batch(items: list[dict]) -> dict[int, str]:
    if not items:
        return {}

    payload = [
        {
            "id": it["id"],
            "note_type": it.get("note_type", ""),
            "text": it.get("text", ""),
        }
        for it in items
    ]
    user = f"Classify payment status for each note line:\n{json.dumps(payload, ensure_ascii=False)}"
    parsed = groq_chat_json(_STATUS_SYSTEM, user, max_tokens=2048)
    if not parsed:
        return {}

    rows = parsed.get("results", parsed) if isinstance(parsed, dict) else parsed
    if not isinstance(rows, list):
        return {}

    out: dict[int, str] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        rid = row.get("id")
        if rid is None:
            continue
        out[int(rid)] = _sanitize_status(row.get("status", "Unknown"))
    return out


def apply_note_statuses(rows: list[dict]) -> None:
    """Set status_raw on each note row dict in place."""
    if not rows:
        return

    if groq_available():
        items = [
            {
                "id": i,
                "text": r.get("note_text", r.get("merchant_raw", "")),
                "note_type": r.get("note_type", ""),
            }
            for i, r in enumerate(rows)
        ]
        chunk_size = 30
        for start in range(0, len(items), chunk_size):
            chunk = items[start : start + chunk_size]
            results = _groq_status_batch(chunk)
            for it in chunk:
                idx = it["id"]
                if idx in results:
                    rows[idx]["status_raw"] = results[idx]
                else:
                    rows[idx]["status_raw"] = _status_fallback(
                        rows[idx].get("note_type", ""),
                        rows[idx].get("note_text", ""),
                    )
    else:
        for r in rows:
            r["status_raw"] = _status_fallback(
                r.get("note_type", ""),
                r.get("note_text", ""),
            )
