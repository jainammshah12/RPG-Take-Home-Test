from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from src.config import SHOEBOX_DIR

RECEIPT_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tiff", ".tif")
STATEMENT_EXTENSIONS = (".pdf",)
INVOICE_EXTENSIONS = (".xlsx", ".xls")
NOTES_EXTENSIONS = (".txt", ".md")


@dataclass
class IngestedFiles:
    receipt_paths: list[Path] = field(default_factory=list)
    statement_paths: list[Path] = field(default_factory=list)
    invoice_paths: list[Path] = field(default_factory=list)
    notes_paths: list[Path] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)

    @property
    def receipt_count(self) -> int:
        return len(self.receipt_paths)

    @property
    def statement_path(self) -> Path | None:
        """Primary statement (first PDF) — backward compatible."""
        return self.statement_paths[0] if self.statement_paths else None

    @property
    def invoices_path(self) -> Path | None:
        return self.invoice_paths[0] if self.invoice_paths else None

    @property
    def notes_path(self) -> Path | None:
        return self.notes_paths[0] if self.notes_paths else None


def _unique_paths(paths: list[Path]) -> list[Path]:
    seen: set[str] = set()
    out: list[Path] = []
    for path in sorted(paths):
        key = str(path.resolve()).lower()
        if key not in seen:
            seen.add(key)
            out.append(path)
    return out


def ingest(shoebox_dir: Path | None = None) -> IngestedFiles:
    base = shoebox_dir or SHOEBOX_DIR
    result = IngestedFiles()

    if not base.is_dir():
        result.missing.append("shoebox/")
        return result

    receipts_dir = base / "receipts"
    if receipts_dir.is_dir():
        found: list[Path] = []
        for path in receipts_dir.iterdir():
            if path.is_file() and path.suffix.lower() in RECEIPT_EXTENSIONS:
                found.append(path)
        result.receipt_paths = _unique_paths(found)
    if not result.receipt_paths:
        result.missing.append("receipts/")

    statements = [
        p for p in base.iterdir()
        if p.is_file() and p.suffix.lower() in STATEMENT_EXTENSIONS
    ]
    result.statement_paths = _unique_paths(statements)
    if not result.statement_paths:
        result.missing.append("*.pdf (statement)")

    invoices = [
        p for p in base.iterdir()
        if p.is_file() and p.suffix.lower() in INVOICE_EXTENSIONS
    ]
    result.invoice_paths = _unique_paths(invoices)
    if not result.invoice_paths:
        result.missing.append("*.xlsx (invoices)")

    notes = [
        p for p in base.iterdir()
        if p.is_file() and p.suffix.lower() in NOTES_EXTENSIONS
    ]
    result.notes_paths = _unique_paths(notes)
    if not result.notes_paths:
        result.missing.append("notes.txt")

    return result
