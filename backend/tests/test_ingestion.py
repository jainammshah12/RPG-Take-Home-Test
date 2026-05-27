from src.config import SHOEBOX_DIR
from src.ingestion.loader import ingest


def test_ingest_discovers_all_shoebox_files():
    result = ingest(SHOEBOX_DIR)

    assert result.receipt_count >= 1
    assert any(p.suffix.lower() == ".pdf" for p in result.statement_paths)
    assert any(p.suffix.lower() in {".xlsx", ".xls"} for p in result.invoice_paths)
    assert any(p.suffix.lower() in {".txt", ".md"} for p in result.notes_paths)
