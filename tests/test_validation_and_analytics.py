import pandas as pd

from src.analytics.metrics import compute_analytics
from src.validation import validate


def _sample_transactions() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "source": "invoice",
                "merchant": "BrightPath Marketing",
                "amount": 3500.0,
                "date": "2025-03-04",
                "currency": "CAD",
            },
            {
                "source": "statement",
                "merchant": "STAPLES #0312",
                "amount": -45.99,
                "date": "2025-03-10",
                "currency": "CAD",
            },
        ]
    )


def test_validate_builds_display_dataframe():
    tx = _sample_transactions()
    result = validate(tx)

    assert result.row_count == len(tx)
    # Display frame should be safe to render in Streamlit tables
    assert not result.display_df.empty
    assert set(["date", "amount", "merchant", "source"]).issubset(result.display_df.columns)
    # No fundamental schema errors expected for this simple sample
    assert result.valid


def test_compute_analytics_basic_metrics():
    tx = _sample_transactions()
    a = compute_analytics(tx, parsed={})

    assert a.revenue > 0
    assert a.expenses > 0
    assert isinstance(a.cash_flow, float)
    # By-source breakdown should contain both invoice and statement
    assert not a.by_source.empty
    assert set(a.by_source["source"]) >= {"invoice", "statement"}

