import pandas as pd

from src.enrichment.categorizer import UNKNOWN, assign_categories, categorize_merchant


def test_categorize_known_merchants():
    assert categorize_merchant("STAPLES #4421") == "OFFICE_SUPPLIES"
    assert categorize_merchant("AMZN WEB SERVICES") == "SOFTWARE"
    assert categorize_merchant("Starbucks Ottawa") == "MEALS_AND_ENTERTAINMENT"
    assert categorize_merchant("UBER TRIP") == "TRAVEL"


def test_categorize_unknown_when_no_match():
    assert categorize_merchant("Random Vendor XYZ") == UNKNOWN
    assert categorize_merchant("") == UNKNOWN


def test_categorize_unknown_when_ambiguous():
    # "client" could match CLIENT_EXPENSES hint rules; merchant with conflicting signals
    assert categorize_merchant("Uber Software Consulting") == UNKNOWN


def test_category_hint_used_when_merchant_unmatched():
    assert categorize_merchant("Misc charge", "Software & Cloud") == "SOFTWARE"


def test_assign_categories_adds_column():
    df = pd.DataFrame(
        [
            {"merchant": "STAPLES", "amount": -10.0},
            {"merchant": "Mystery Shop", "amount": -5.0},
        ]
    )
    out = assign_categories(df)
    assert "category" in out.columns
    assert out.iloc[0]["category"] == "OFFICE_SUPPLIES"
    assert out.iloc[1]["category"] == UNKNOWN
