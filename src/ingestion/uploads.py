"""Save user-uploaded documents into the shoebox."""

from __future__ import annotations

import re
from pathlib import Path

from src.ingestion.loader import INVOICE_EXTENSIONS, NOTES_EXTENSIONS, RECEIPT_EXTENSIONS, STATEMENT_EXTENSIONS

_RECEIPT_EXTS = {e.lstrip(".") for e in RECEIPT_EXTENSIONS}


def _safe_filename(name: str) -> str:
    name = Path(name).name
    name = re.sub(r"[^\w.\- ]", "_", name)
    return name.strip() or "upload"


def save_receipts(shoebox: Path, files: list) -> list[str]:
    dest_dir = shoebox / "receipts"
    dest_dir.mkdir(parents=True, exist_ok=True)
    saved: list[str] = []

    for uploaded in files:
        name = _safe_filename(uploaded.name)
        ext = Path(name).suffix.lower().lstrip(".")
        if ext not in _RECEIPT_EXTS:
            name = f"{name}.jpg"
        path = dest_dir / name
        if path.exists():
            stem, suffix = path.stem, path.suffix
            n = 1
            while path.exists():
                path = dest_dir / f"{stem}_{n}{suffix}"
                n += 1
        path.write_bytes(uploaded.getvalue())
        saved.append(path.name)
    return saved


def save_statement(shoebox: Path, uploaded) -> str | None:
    if uploaded is None:
        return None
    name = _safe_filename(uploaded.name)
    if not name.lower().endswith(".pdf"):
        name = f"{name}.pdf"
    path = shoebox / name
    path.write_bytes(uploaded.getvalue())
    return path.name


def save_invoices(shoebox: Path, uploaded) -> str | None:
    if uploaded is None:
        return None
    name = _safe_filename(uploaded.name)
    if not any(name.lower().endswith(ext) for ext in INVOICE_EXTENSIONS):
        name = f"{name}.xlsx"
    path = shoebox / name
    path.write_bytes(uploaded.getvalue())
    return path.name


def append_notes(shoebox: Path, text: str, uploaded=None) -> str | None:
    if uploaded is not None:
        content = uploaded.getvalue().decode("utf-8", errors="replace")
        name = _safe_filename(uploaded.name)
        path = shoebox / name
        if path.exists():
            existing = path.read_text(encoding="utf-8", errors="replace")
            path.write_text(existing.rstrip() + "\n\n" + content, encoding="utf-8")
        else:
            path.write_text(content, encoding="utf-8")
        return path.name

    if not text or not text.strip():
        return None

    path = shoebox / "notes.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    block = text.strip()
    if path.exists():
        existing = path.read_text(encoding="utf-8", errors="replace").rstrip()
        path.write_text(f"{existing}\n\n{block}", encoding="utf-8")
    else:
        path.write_text(block, encoding="utf-8")
    return path.name
