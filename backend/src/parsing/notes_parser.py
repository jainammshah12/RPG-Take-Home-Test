import re
from pathlib import Path

import pandas as pd

# Structured line: date | merchant | amount | category
_PIPE = re.compile(
    r"(\d{4}-\d{2}-\d{2})\s*\|\s*(.+?)\s*\|\s*\$?([\d,]+\.?\d*)\s*(?:\|\s*(.+))?$"
)
_ALT = re.compile(
    r"(.+?)\s*-\s*\$?([\d,]+\.?\d*)\s+on\s+(\d{4}-\d{2}-\d{2})",
    re.IGNORECASE,
)
_TAG_LINE = re.compile(r"^\[(todo|done)\]\s*(.+)$", re.IGNORECASE)
_MONEY = re.compile(r"(?:~?\$|CAD\s*|USD\s*)([\d,]+\.?\d*)", re.IGNORECASE)

_MERCHANT_HINTS: tuple[tuple[str, str], ...] = (
    (r"greenloop", "GreenLoop Technologies"),
    (r"atelier\s+nomade", "Atelier Nomade"),
    (r"brightpath", "BrightPath Marketing"),
    (r"adobe", "Adobe"),
    (r"staples", "Staples"),
    (r"petco", "Petco"),
    (r"netflix", "Netflix"),
    (r"nonna'?s?\s+kitchen", "Nonna's Kitchen"),
)


def parse_notes(notes_path: Path) -> pd.DataFrame:
    text = notes_path.read_text(encoding="utf-8", errors="replace")
    rows: list[dict] = []
    rows.extend(_parse_tagged_lines(text, notes_path.name))
    rows.extend(_parse_structured_lines(text, notes_path.name))
    rows.extend(_parse_inline_mentions(text, notes_path.name))

    if not rows:
        return pd.DataFrame(
            columns=[
                "source",
                "date_raw",
                "merchant_raw",
                "amount",
                "category_hint",
                "status_raw",
                "source_file",
                "note_type",
            ]
        )
    return pd.DataFrame(rows)


def parse_all_notes(notes_paths: list[Path]) -> pd.DataFrame:
    frames = []
    for path in notes_paths:
        df = parse_notes(path)
        if not df.empty:
            frames.append(df)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def _parse_tagged_lines(text: str, source_file: str) -> list[dict]:
    """Parse [todo] / [done] lines; skip the 'random:' section."""
    rows: list[dict] = []
    in_random = False

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.lower().startswith("random:"):
            in_random = True
            continue
        if in_random:
            continue
        if stripped.startswith("==") or stripped.startswith("#"):
            continue

        tag_match = _TAG_LINE.match(stripped)
        if not tag_match:
            continue

        tag = tag_match.group(1).lower()
        body = tag_match.group(2).strip()
        merchant = _merchant_from_text(body)
        status_raw = _status_from_tag(tag, body)
        amount = _amount_from_text(body)
        note_type = "todo" if tag == "todo" else "done"

        rows.append(
            _note_row(
                date_raw="",
                merchant=merchant,
                amount=amount,
                category_hint="",
                status_raw=status_raw,
                source_file=source_file,
                note_type=note_type,
            )
        )
    return rows


def _parse_structured_lines(text: str, source_file: str) -> list[dict]:
    rows: list[dict] = []
    in_random = False

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.lower().startswith("random:"):
            in_random = True
            continue
        if in_random or line.startswith("[") or line.startswith("=="):
            continue

        pipe = _PIPE.match(line)
        if pipe:
            rows.append(
                _note_row(
                    pipe.group(1),
                    pipe.group(2),
                    float(pipe.group(3).replace(",", "")),
                    pipe.group(4) or "",
                    "Unknown",
                    source_file,
                    "expense",
                )
            )
            continue

        alt = _ALT.match(line)
        if alt:
            rows.append(
                _note_row(
                    alt.group(3),
                    alt.group(1),
                    float(alt.group(2).replace(",", "")),
                    "",
                    "Unknown",
                    source_file,
                    "expense",
                )
            )
    return rows


def _parse_inline_mentions(text: str, source_file: str) -> list[dict]:
    """Bullet lines with dollar amounts (petco, netflix, refunds)."""
    rows: list[dict] = []
    in_random = False

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.lower().startswith("random:"):
            in_random = True
            continue
        if in_random or stripped.startswith("["):
            continue
        if not stripped.startswith("-") and "$" not in stripped:
            continue

        amounts = _MONEY.findall(stripped)
        if not amounts:
            continue

        low = stripped.lower()
        merchant = _merchant_from_text(stripped)
        amt = float(amounts[0].replace(",", ""))
        status_raw = "Refunded" if "refund" in low else "Unknown"
        if "refund" in low:
            amt = abs(amt)
        else:
            amt = -abs(amt)

        rows.append(
            _note_row("", merchant, amt, "", status_raw, source_file, "expense")
        )
    return rows


def _merchant_from_text(text: str) -> str:
    low = text.lower()
    for pattern, label in _MERCHANT_HINTS:
        if re.search(pattern, low):
            return label
    return "Note mention"


def _status_from_tag(tag: str, body: str) -> str:
    low = body.lower()
    if tag == "todo":
        return "Pending"
    if "refund" in low:
        return "Refunded"
    if "paid" in low or "sent and paid" in low:
        return "Paid"
    if "outstanding" in low or "hasn't paid" in low or "unpaid" in low:
        return "Pending"
    return "Paid"


def _amount_from_text(text: str) -> float | None:
    amounts = _MONEY.findall(text)
    if not amounts:
        return None
    val = float(amounts[0].replace(",", ""))
    low = text.lower()
    if "refund" in low:
        return abs(val)
    if "paid" in low and "refund" not in low:
        return abs(val)
    return -abs(val) if val > 0 else val


def _note_row(
    date_raw: str,
    merchant: str,
    amount: float | None,
    category_hint: str,
    status_raw: str,
    source_file: str,
    note_type: str,
) -> dict:
    return {
        "source": "note",
        "date_raw": date_raw,
        "merchant_raw": merchant.strip(),
        "amount": amount,
        "category_hint": category_hint.strip(),
        "status_raw": status_raw,
        "source_file": source_file,
        "note_type": note_type,
    }
