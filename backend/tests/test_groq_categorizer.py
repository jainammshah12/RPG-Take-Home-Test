from unittest.mock import patch

import pandas as pd

from src.enrichment.categorizer import UNKNOWN, assign_categories


def test_assign_categories_uses_groq_batch():
    df = pd.DataFrame(
        [
            {"merchant": "Mystery Vendor", "category_hint": "cloud software"},
            {"merchant": "STAPLES", "category_hint": ""},
        ]
    )
    mock = {
        "results": [
            {"id": 0, "category": "SOFTWARE"},
            {"id": 1, "category": "OFFICE_SUPPLIES"},
        ]
    }

    with patch("src.enrichment.categorizer.groq_available", return_value=True):
        with patch("src.enrichment.categorizer._groq_categorize_batch", return_value={0: "SOFTWARE", 1: "OFFICE_SUPPLIES"}):
            out = assign_categories(df)

    assert out.iloc[0]["category"] == "SOFTWARE"
    assert out.iloc[1]["category"] == "OFFICE_SUPPLIES"


def test_assign_categories_rules_when_no_groq():
    df = pd.DataFrame([{"merchant": "STAPLES", "amount": -10.0}])
    with patch("src.enrichment.categorizer.groq_available", return_value=False):
        out = assign_categories(df)
    assert out.iloc[0]["category"] == "OFFICE_SUPPLIES"


def test_groq_unknown_falls_back_to_rules():
    df = pd.DataFrame([{"merchant": "STAPLES", "amount": -10.0}])
    with patch("src.enrichment.categorizer.groq_available", return_value=True):
        with patch("src.enrichment.categorizer._groq_categorize_batch", return_value={0: UNKNOWN}):
            out = assign_categories(df)
    assert out.iloc[0]["category"] == "OFFICE_SUPPLIES"
