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
    assert pd.to_datetime(row["date"]).strftime("%Y-%m-%d") == "2025-03-10"
