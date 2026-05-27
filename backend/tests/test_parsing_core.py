import pandas as pd
import pytest

from src.config import SHOEBOX_DIR
from src.parsing.invoice_parser import parse_invoices
from src.parsing.notes_parser import parse_notes
from src.parsing.statement_parser import parse_statement


@pytest.fixture
def statement_pdf():
    path = SHOEBOX_DIR / "Visa_Statement_Q12025.pdf"
    if not path.is_file():
        pytest.skip(f"Sample statement not found: {path}")
    return path


@pytest.fixture
def invoices_xlsx():
    path = SHOEBOX_DIR / "invoices.xlsx"
    if not path.is_file():
        pytest.skip(f"Sample invoices not found: {path}")
    return path


@pytest.fixture
def notes_txt():
    path = SHOEBOX_DIR / "notes.txt"
    if not path.is_file():
        pytest.skip(f"Sample notes not found: {path}")
    return path


def test_parse_statement_visa_q1(statement_pdf):
    df = parse_statement(statement_pdf)

    assert not df.empty
    assert {"source", "date_raw", "merchant_raw", "amount", "source_file"} <= set(df.columns)
    assert df["source"].unique().tolist() == ["statement"]
    assert set(df["source_file"].unique()) == {statement_pdf.name}
    assert df["amount"].notna().all()


def test_parse_invoices_structure(invoices_xlsx):
    df = parse_invoices(invoices_xlsx)

    assert not df.empty
    assert {"source", "invoice_id", "date_raw", "merchant_raw", "amount", "status_raw", "source_file"} <= set(
        df.columns
    )
    assert df["source"].unique().tolist() == ["invoice"]
    assert set(df["source_file"].unique()) == {invoices_xlsx.name}
    assert set(df["status_raw"].unique()).issubset({"paid", "pending"})


def test_parse_notes_heuristics_work_for_unstructured_file(notes_txt):
    df = parse_notes(notes_txt)

    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert {"source", "merchant_raw", "status_raw", "source_file"} <= set(df.columns)
    assert set(df["source_file"].unique()) == {notes_txt.name}
    # random: section must not produce rows
    merchants = df["merchant_raw"].str.lower()
    assert not merchants.str.contains("nonna", na=False).any()
    assert merchants.str.contains("greenloop", na=False).any()
    assert set(df["status_raw"].unique()) <= {"Paid", "Pending", "Refunded", "Unknown"}
