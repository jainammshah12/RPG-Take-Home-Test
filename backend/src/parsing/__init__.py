from __future__ import annotations

import pandas as pd

from src.ingestion.loader import IngestedFiles
from src.parsing.invoice_parser import parse_all_invoices
from src.parsing.notes_parser import parse_all_notes
from src.parsing.receipt_ocr import parse_receipts
from src.parsing.statement_parser import parse_statements


def parse_all(ingested: IngestedFiles) -> dict[str, pd.DataFrame]:
    result: dict[str, pd.DataFrame] = {}

    result["receipts"] = parse_receipts(ingested.receipt_paths)
    result["statement"] = parse_statements(ingested.statement_paths)
    result["invoices"] = parse_all_invoices(ingested.invoice_paths)
    result["notes"] = parse_all_notes(ingested.notes_paths)

    return result
