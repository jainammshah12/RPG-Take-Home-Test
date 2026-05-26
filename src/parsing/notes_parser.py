import json
import os
import re
from pathlib import Path

import pandas as pd

# Structured line formats (fast path)
_PIPE = re.compile(
    r"(\d{4}-\d{2}-\d{2})\s*\|\s*(.+?)\s*\|\s*\$?([\d,]+\.?\d*)\s*(?:\|\s*(.+))?$"
)
_ALT = re.compile(
    r"(.+?)\s*-\s*\$?([\d,]+\.?\d*)\s+on\s+(\d{4}-\d{2}-\d{2})",
    re.IGNORECASE,
)
# Inline mentions: "petco charge", "~$40 refund", "$16.99 netflix"
_MONEY_MENTION = re.compile(
    r"(?:~?\$|CAD\s*|USD\s*)([\d,]+\.?\d*)",
    re.IGNORECASE,
)


def parse_notes(notes_path: Path) -> pd.DataFrame:
    text = notes_path.read_text(encoding="utf-8", errors="replace")
    rows = _parse_structured_lines(text, notes_path.name)

    if len(rows) < 2:
        llm_rows = _parse_notes_with_gemini(text, notes_path.name)
        rows.extend(llm_rows)

    if not rows:
        rows = _parse_heuristic_mentions(text, notes_path.name)

    return pd.DataFrame(rows) if rows else pd.DataFrame(
        columns=["source", "date_raw", "merchant_raw", "amount", "category_hint", "source_file", "note_type"]
    )


def parse_all_notes(notes_paths: list[Path]) -> pd.DataFrame:
    frames = []
    for path in notes_paths:
        df = parse_notes(path)
        if not df.empty:
            frames.append(df)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def _parse_structured_lines(text: str, source_file: str) -> list[dict]:
    rows: list[dict] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("["):
            continue

        pipe = _PIPE.match(line)
        if pipe:
            rows.append(_note_row(pipe.group(1), pipe.group(2), float(pipe.group(3).replace(",", "")), pipe.group(4) or "", source_file))
            continue

        alt = _ALT.match(line)
        if alt:
            rows.append(_note_row(alt.group(3), alt.group(1), float(alt.group(2).replace(",", "")), "", source_file))
    return rows


def _note_row(date_raw: str, merchant: str, amount: float, category_hint: str, source_file: str) -> dict:
    return {
        "source": "note",
        "date_raw": date_raw,
        "merchant_raw": merchant.strip(),
        "amount": amount,
        "category_hint": category_hint.strip(),
        "source_file": source_file,
        "note_type": "expense",
    }


def _parse_heuristic_mentions(text: str, source_file: str) -> list[dict]:
    """Extract obvious dollar mentions from informal notes."""
    rows: list[dict] = []
    keywords = {
        "petco": "Petco",
        "netflix": "Netflix",
        "staples": "Staples",
        "adobe": "Adobe",
        "greenloop": "GreenLoop",
        "refund": "Refund",
    }
    for line in text.splitlines():
        low = line.lower()
        if not any(k in low for k in keywords) and "$" not in line and "refund" not in low:
            continue
        amounts = _MONEY_MENTION.findall(line)
        if not amounts:
            continue
        merchant = "Note mention"
        for key, label in keywords.items():
            if key in low:
                merchant = label
                break
        amt = float(amounts[0].replace(",", ""))
        if "refund" in low:
            amt = abs(amt)
        rows.append(
            {
                "source": "note",
                "date_raw": "",
                "merchant_raw": merchant,
                "amount": -amt if "refund" not in low and "paid" not in low else amt,
                "category_hint": "Personal" if "netflix" in low or "petco" in low else "",
                "source_file": source_file,
                "note_type": "info",
            }
        )
    return rows


def _parse_notes_with_gemini(text: str, source_file: str) -> list[dict]:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key or len(text.strip()) < 20:
        return []

    try:
        from google import genai
        from google.genai import types
    except ImportError:
        return []

    prompt = """You are a financial notes parser. Read these informal business notes and extract
any mentions of money, expenses, refunds, invoices, or payments.

Return ONLY a JSON array. Each object must have:
  merchant   (string) — who/what the money relates to
  amount     (number) — positive for income/refunds, negative for expenses (best guess)
  date       (string|null) — YYYY-MM-DD if inferable, else null
  category_hint (string) — short category label
  note_type  (string) — one of: expense, revenue, refund, info, todo

Skip pure todos with no dollar amount. Output raw JSON only, no markdown."""

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[prompt, text[:8000]],
            config=types.GenerateContentConfig(temperature=0, max_output_tokens=2048),
        )
        raw = (response.text or "").strip()
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.DOTALL).strip()
        items = json.loads(raw)
    except Exception:
        return []

    rows: list[dict] = []
    if not isinstance(items, list):
        return rows

    for item in items:
        if not isinstance(item, dict):
            continue
        amt = item.get("amount")
        if amt is None:
            continue
        rows.append(
            {
                "source": "note",
                "date_raw": item.get("date") or "",
                "merchant_raw": str(item.get("merchant", "Unknown")),
                "amount": float(amt),
                "category_hint": str(item.get("category_hint", "")),
                "source_file": source_file,
                "note_type": str(item.get("note_type", "info")),
            }
        )
    return rows
