import pandas as pd

from src.cleaning.normalizer import combine_sources


def test_combine_sources_normalizes_dates_and_merchants():
    parsed = {
        "statement": pd.DataFrame(
            [
                {
                    "source": "statement",
                    "source_file": "card.pdf",
                    "date_raw": "2025-03-10",
                    "merchant_raw": "STAPLES #0312",
                    "amount": -45.99,
                },
                {
                    "source": "statement",
                    "source_file": "card.pdf",
                    "date_raw": "2025-03-10",
                    "merchant_raw": "STAPLES #0312",
                    "amount": -45.99,
                },
            ]
        )
    }

    combined = combine_sources(parsed)

    assert len(combined) == 1
    row = combined.iloc[0]
    assert str(row["merchant"]) == "Staples"
    assert str(row["merchant_group"]) == "Staples"
    assert row["status"] == "Unknown"
    assert pd.to_datetime(row["date"]).strftime("%Y-%m-%d") == "2025-03-10"


def test_combine_sources_normalizes_invoice_status():
    parsed = {
        "invoices": pd.DataFrame(
            [
                {
                    "source": "invoice",
                    "source_file": "invoices.xlsx",
                    "invoice_id": "1",
                    "date_raw": "2025-01-15",
                    "merchant_raw": "Client A — Work",
                    "amount": 100.0,
                    "status_raw": "paid",
                },
                {
                    "source": "invoice",
                    "source_file": "invoices.xlsx",
                    "invoice_id": "2",
                    "date_raw": "2025-02-01",
                    "merchant_raw": "Client A — More work",
                    "amount": 200.0,
                    "status_raw": "pending",
                },
            ]
        )
    }
    combined = combine_sources(parsed)
    assert set(combined["status"].unique()) == {"Paid", "Pending"}
    assert combined["merchant_group"].nunique() == 1


def test_combine_sources_dedupes_duplicate_invoices():
    parsed = {
        "invoices": pd.DataFrame(
            [
                {
                    "source": "invoice",
                    "source_file": "invoices.xlsx",
                    "invoice_id": "INV-100",
                    "date_raw": "2025-01-15",
                    "merchant_raw": "Client A",
                    "amount": 500.0,
                    "status_raw": "paid",
                },
                {
                    "source": "invoice",
                    "source_file": "invoices.xlsx",
                    "invoice_id": "INV-100",
                    "date_raw": "2025-01-15",
                    "merchant_raw": "Client A",
                    "amount": 500.0,
                    "status_raw": "paid",
                },
            ]
        )
    }
    combined = combine_sources(parsed)
    assert len(combined) == 1
