"""Rule-based expense categorization from merchant names and note hints."""

from __future__ import annotations

import re

import pandas as pd

UNKNOWN = "UNKNOWN"

CATEGORIES = (
    "SOFTWARE",
    "TRAVEL",
    "MEALS_AND_ENTERTAINMENT",
    "OFFICE_SUPPLIES",
    "PROFESSIONAL_SERVICES",
    "EQUIPMENT",
    "SUBSCRIPTIONS",
    "BANKING_AND_FEES",
    "CLIENT_EXPENSES",
    "UTILITIES",
    "OTHER",
    UNKNOWN,
)

# (category, merchant substrings) — first match wins only when uniquely determined
_MERCHANT_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("SOFTWARE", ("aws", "amazon", "amzn web", "microsoft", "msft", "adobe", "github", "figma", "slack", "notion", "google", "gcp", "saas", "dropbox", "atlassian", "jetbrains")),
    ("TRAVEL", ("uber", "lyft", "airbnb", "hotel", "airline", "expedia", "flight", "marriott", "hilton", "air canada", "westjet", "parking")),
    ("MEALS_AND_ENTERTAINMENT", ("starbucks", "tim hortons", "restaurant", "cafe", "coffee", "mcdonald", "doordash", "ubereats", "uber eats", "dining", "pub", "bar & grill")),
    ("OFFICE_SUPPLIES", ("staples", "office depot", "office max", "grand & toy")),
    ("PROFESSIONAL_SERVICES", ("consulting", "consultant", "legal", "law firm", "accountant", "accounting", "bookkeeping", "upwork", "fiverr", "notary")),
    ("EQUIPMENT", ("apple store", "best buy", "dell", "lenovo", "canada computers", "memory express")),
    ("SUBSCRIPTIONS", ("netflix", "spotify", "subscription", "membership", "patreon", "linkedin premium")),
    ("BANKING_AND_FEES", ("bank fee", "service charge", "interest charge", "atm fee", "overdraft", "wire fee", "annual fee")),
    ("CLIENT_EXPENSES", ("client expense", "client reimb", "on behalf of client", "billable expense")),
    ("UTILITIES", ("hydro", "electric", "enbridge", "gas bill", "internet", "rogers", "bell ", "telus", "shaw", "fido", "utility")),
)

_HINT_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("SOFTWARE", ("software", "cloud", "saas", "hosting")),
    ("TRAVEL", ("travel", "transport", "mileage")),
    ("MEALS_AND_ENTERTAINMENT", ("meal", "meals", "entertainment", "food")),
    ("OFFICE_SUPPLIES", ("office", "supplies")),
    ("PROFESSIONAL_SERVICES", ("professional", "legal", "consulting")),
    ("EQUIPMENT", ("equipment", "hardware")),
    ("SUBSCRIPTIONS", ("subscription", "membership")),
    ("BANKING_AND_FEES", ("bank", "fee", "fees")),
    ("CLIENT_EXPENSES", ("client", "reimburs")),
    ("UTILITIES", ("utility", "utilities", "internet", "phone")),
    ("OTHER", ("other", "misc")),
)


def _normalize_text(val) -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    s = str(val).strip().lower()
    s = re.sub(r"\s+#\d+", "", s)
    s = re.sub(r"[^a-z0-9&*+\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _matching_categories(text: str, rules: tuple[tuple[str, tuple[str, ...]], ...]) -> set[str]:
    if not text:
        return set()
    matches: set[str] = set()
    for category, keywords in rules:
        for kw in keywords:
            if kw in text:
                matches.add(category)
                break
    return matches


def categorize_merchant(merchant: str, category_hint: str = "") -> str:
    """Return a single category, or UNKNOWN when no rule matches or rules conflict."""
    merchant_text = _normalize_text(merchant)
    merchant_matches = _matching_categories(merchant_text, _MERCHANT_RULES)

    if len(merchant_matches) > 1:
        return UNKNOWN
    if len(merchant_matches) == 1:
        return next(iter(merchant_matches))

    hint_text = _normalize_text(category_hint)
    hint_matches = _matching_categories(hint_text, _HINT_RULES)
    if len(hint_matches) == 1:
        return next(iter(hint_matches))
    if len(hint_matches) > 1:
        return UNKNOWN
    return UNKNOWN


def assign_categories(transactions: pd.DataFrame) -> pd.DataFrame:
    if transactions.empty:
        out = transactions.copy()
        out["category"] = pd.Series(dtype=str)
        return out

    out = transactions.copy()

    def _row_category(row: pd.Series) -> str:
        merchant = row.get("merchant") or row.get("merchant_raw") or ""
        hint = row.get("category_hint", "")
        return categorize_merchant(str(merchant), str(hint) if hint is not None and not pd.isna(hint) else "")

    out["category"] = out.apply(_row_category, axis=1)
    return out
