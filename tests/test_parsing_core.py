from pathlib import Path

import pandas as pd

from src.parsing.invoice_parser import parse_invoices
from src.parsing.notes_parser import parse_notes
from src.parsing.statement_parser import parse_statement


def test_parse_statement_visa_q1():
    pdf_path = Path("shoebox") / "Visa_Statement_Q12025.pdf"
    df = parse_statement(pdf_path)

    # Should parse multiple rows with date, merchant, amount
    assert not df.empty
    assert {"source", "date_raw", "merchant_raw", "amount", "source_file"} <= set(df.columns)
    # All rows must be tagged as statement from the same file
    assert df["source"].unique().tolist() == ["statement"]
    assert set(df["source_file"].unique()) == {pdf_path.name}
    assert df["amount"].notna().all()


def test_parse_invoices_structure():
    xlsx = Path("shoebox") / "invoices.xlsx"
    df = parse_invoices(xlsx)

    assert not df.empty
    assert {"source", "invoice_id", "date_raw", "merchant_raw", "amount", "status", "source_file"} <= set(df.columns)
    # All rows should come from a single workbook and be tagged as invoices
    assert df["source"].unique().tolist() == ["invoice"]
    assert set(df["source_file"].unique()) == {xlsx.name}
    # Status should be normalised
    assert set(df["status"].unique()).issubset({"paid", "pending"})


def test_parse_notes_heuristics_work_for_unstructured_file():
    notes_path = Path("shoebox") / "notes.txt"
    df = parse_notes(notes_path)

    # For the provided notes.txt we at least want one extracted row
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert {"source", "merchant_raw", "amount", "source_file"} <= set(df.columns)
    # All rows must reference the notes file
    assert set(df["source_file"].unique()) == {notes_path.name}

