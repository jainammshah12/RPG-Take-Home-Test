from pathlib import Path

from src.ingestion.loader import ingest


def test_ingest_discovers_all_shoebox_files():
    base = Path("shoebox")
    result = ingest(base)

    # We expect at least one receipt, one statement PDF, one invoice workbook, and notes.
    assert result.receipt_count >= 1
    assert any(p.suffix.lower() == ".pdf" for p in result.statement_paths)
    assert any(p.suffix.lower() in {".xlsx", ".xls"} for p in result.invoice_paths)
    assert any(p.suffix.lower() in {".txt", ".md"} for p in result.notes_paths)

