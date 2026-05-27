import re
from datetime import datetime
from pathlib import Path

import pandas as pd
import pdfplumber

# TXN-0103-001 Jan 03 GOOGLE *WORKSPACE $8.28
_TXN_LINE = re.compile(
    r"^(?:TXN-\S+\s+)?"
    r"([A-Za-z]{3}\s+\d{1,2})\s+"
    r"(.+?)\s+"
    r"([\u2212\u2013\u2014\-]?\$[\d,]+\.\d{2})\s*$"
)

# 2025-03-05  STARBUCKS #239  $-6.45
_ISO_LINE = re.compile(
    r"^(\d{4}-\d{2}-\d{2})\s+(.+?)\s+(\$-?[\d,]+\.\d{2}|-?\$?[\d,]+\.\d{2})\s*$"
)

_MONTH_HEADER = re.compile(
    r"^(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})$",
    re.IGNORECASE,
)

_PERIOD_YEAR = re.compile(r"(20\d{2})")
_SKIP_PREFIXES = ("trans id", "date", "description", "amount", "page ", "national credit", "this statement", "account")


def _parse_amount(raw: str) -> float | None:
    if not raw:
        return None
    s = raw.strip()
    negative = bool(re.match(r"^[\u2212\u2013\u2014\-]", s)) or s.startswith("$-")
    s = re.sub(r"^[\u2212\u2013\u2014\-]", "", s)
    s = s.replace("$", "").replace(",", "").strip()
    try:
        val = float(s)
        return -val if negative else val
    except ValueError:
        return None


def _month_day_to_iso(month_day: str, year: int, month_hint: str | None = None) -> str:
    try:
        dt = datetime.strptime(f"{month_day} {year}", "%b %d %Y")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        pass
    if month_hint:
        try:
            dt = datetime.strptime(f"{month_day} {month_hint} {year}", "%d %B %Y")
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass
    return month_day


def _infer_year(text: str) -> int:
    for pat in (
        r"Statement Date:\s*\w+\s+\d{1,2},?\s+(20\d{2})",
        r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}[^\d]*(20\d{2})",
        r"(20\d{2})",
    ):
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return int(m.group(m.lastindex))
    return datetime.now().year


def _infer_default_year(text: str) -> int:
    return _infer_year(text[:800])


def parse_statement(pdf_path: Path) -> pd.DataFrame:
    rows: list[dict] = []
    full_text = ""

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            full_text += (page.extract_text() or "") + "\n"

    default_year = _infer_default_year(full_text)
    current_month: str | None = None

    for line in full_text.splitlines():
        line = line.strip()
        if not line:
            continue

        low = line.lower()
        if any(low.startswith(p) for p in _SKIP_PREFIXES):
            continue

        month_hdr = _MONTH_HEADER.match(line)
        if month_hdr:
            current_month = month_hdr.group(1)
            default_year = int(month_hdr.group(2))
            continue

        iso = _ISO_LINE.match(line)
        if iso:
            rows.append(
                {
                    "source": "statement",
                    "date_raw": iso.group(1),
                    "merchant_raw": iso.group(2).strip(),
                    "amount": _parse_amount(iso.group(3)),
                    "source_file": pdf_path.name,
                }
            )
            continue

        txn = _TXN_LINE.match(line)
        if txn:
            month_day = txn.group(1)
            date_raw = _month_day_to_iso(month_day, default_year, current_month)
            rows.append(
                {
                    "source": "statement",
                    "date_raw": date_raw,
                    "merchant_raw": txn.group(2).strip(),
                    "amount": _parse_amount(txn.group(3)),
                    "source_file": pdf_path.name,
                }
            )

    if not rows:
        rows = _parse_tables(pdf_path)

    return pd.DataFrame(rows) if rows else pd.DataFrame(
        columns=["source", "date_raw", "merchant_raw", "amount", "source_file"]
    )


def parse_statements(pdf_paths: list[Path]) -> pd.DataFrame:
    frames = []
    for path in pdf_paths:
        df = parse_statement(path)
        if not df.empty:
            frames.append(df)
    if not frames:
        return pd.DataFrame(columns=["source", "date_raw", "merchant_raw", "amount", "source_file"])
    return pd.concat(frames, ignore_index=True)


def _parse_tables(pdf_path: Path) -> list[dict]:
    rows: list[dict] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables() or []:
                if not table or len(table) < 2:
                    continue
                header = [str(c or "").lower() for c in table[0]]
                date_i = _col_index(header, ("date",))
                desc_i = _col_index(header, ("description", "merchant", "details"))
                amt_i = _col_index(header, ("amount", "total"))
                if desc_i is None or amt_i is None:
                    continue
                for row in table[1:]:
                    if not row or len(row) <= max(desc_i, amt_i):
                        continue
                    rows.append(
                        {
                            "source": "statement",
                            "date_raw": str(row[date_i]) if date_i is not None else "",
                            "merchant_raw": str(row[desc_i]).strip(),
                            "amount": _parse_amount(str(row[amt_i])),
                            "source_file": pdf_path.name,
                        }
                    )
    return rows


def _col_index(header: list[str], names: tuple[str, ...]) -> int | None:
    for i, col in enumerate(header):
        if any(n in col for n in names):
            return i
    return None
