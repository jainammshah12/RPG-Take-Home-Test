"""Expense categorization via Groq (rule-based fallback when no API key)."""

from __future__ import annotations

import re

import pandas as pd

from src.llm.groq_client import groq_available, groq_chat_json

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

_VALID = frozenset(CATEGORIES)

# Rule-based fallback when Groq is unavailable
_MERCHANT_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("SOFTWARE", ("aws", "amazon", "amzn web", "microsoft", "msft", "adobe", "github", "figma", "slack", "notion", "google", "gcp", "saas", "dropbox", "atlassian", "jetbrains", "shopify", "canva", "technologies")),
    ("TRAVEL", ("uber", "lyft", "waymo", "airbnb", "hotel", "airline", "expedia", "flight", "marriott", "hilton", "air canada", "westjet", "parking")),
    ("MEALS_AND_ENTERTAINMENT", ("starbucks", "rest", "tim hortons", "restaurant", "kitchen", "cafe", "coffee", "mcdonald", "doordash", "ubereats", "uber eats", "dining", "pub", "bar & grill")),
    ("OFFICE_SUPPLIES", ("staples", "bureau en gros", "office depot", "office max", "grand & toy")),
    ("PROFESSIONAL_SERVICES", ("consulting", "coworking", "petco", "consultant", "legal", "law firm", "accountant", "accounting", "bookkeeping", "upwork", "fiverr", "notary")),
    ("EQUIPMENT", ("apple store", "best buy", "dell", "lenovo", "canada computers", "memory express")),
    ("SUBSCRIPTIONS", ("netflix", "spotify", "subscription", "membership", "patreon", "linkedin premium")),
    ("BANKING_AND_FEES", ("bank fee", "service charge", "interest charge", "atm fee", "overdraft", "wire fee", "annual fee")),
    ("CLIENT_EXPENSES", ("client expense", "marketing", "client reimb", "on behalf of client", "billable expense")),
    ("UTILITIES", ("hydro", "electric", "enbridge", "jean coutu", "gas bill", "internet", "rogers", "bell ", "telus", "shaw", "fido", "utility", "stationnement", "parking")),
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

_CATEGORIZE_SYSTEM = f"""You categorize small-business expenses.
Return JSON: {{"results": [{{"id": 0, "category": "SOFTWARE"}}, ...]}}
Each category must be exactly one of: {", ".join(c for c in CATEGORIES if c != UNKNOWN)}.
Use UNKNOWN only when the merchant is ambiguous or does not fit any category.
"""


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


def _categorize_merchant_rules(merchant: str, category_hint: str = "") -> str:
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


def _sanitize_category(val: str) -> str:
    cat = str(val or "").strip().upper().replace(" ", "_")
    if cat in _VALID:
        return cat
    return UNKNOWN


def _groq_categorize_batch(items: list[dict]) -> dict[int, str]:
    """items: [{id, merchant, category_hint}]"""
    if not items:
        return {}

    payload = [
        {
            "id": it["id"],
            "merchant": it.get("merchant", ""),
            "category_hint": it.get("category_hint", ""),
        }
        for it in items
    ]
    user = (
        "Categorize each item. Consider merchant name and optional category_hint.\n"
        f"Items:\n{_json_dumps(payload)}"
    )
    parsed = groq_chat_json(_CATEGORIZE_SYSTEM, user)
    if not parsed:
        return {}

    rows = parsed.get("results", parsed) if isinstance(parsed, dict) else parsed
    if not isinstance(rows, list):
        return {}

    out: dict[int, str] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        rid = row.get("id")
        if rid is None:
            continue
        out[int(rid)] = _sanitize_category(row.get("category", UNKNOWN))
    return out


def _json_dumps(obj) -> str:
    import json

    return json.dumps(obj, ensure_ascii=False)


def categorize_merchant(merchant: str, category_hint: str = "") -> str:
    if groq_available():
        batch = _groq_categorize_batch(
            [{"id": 0, "merchant": merchant, "category_hint": category_hint}]
        )
        if 0 in batch:
            return batch[0]
    return _categorize_merchant_rules(merchant, category_hint)


def _row_inputs(out: pd.DataFrame) -> list[dict]:
    items: list[dict] = []
    for i, (_, row) in enumerate(out.iterrows()):
        merchant = row.get("merchant") or row.get("merchant_raw") or ""
        hint = row.get("category_hint", "")
        hint_s = str(hint) if hint is not None and not pd.isna(hint) else ""
        items.append(
            {
                "id": i,
                "merchant": str(merchant),
                "category_hint": hint_s,
            }
        )
    return items


def assign_categories(transactions: pd.DataFrame) -> pd.DataFrame:
    if transactions.empty:
        out = transactions.copy()
        out["category"] = pd.Series(dtype=str)
        return out

    out = transactions.copy()
    items = _row_inputs(out)
    categories: list[str] = [UNKNOWN] * len(out)

    if groq_available():
        chunk_size = 40
        for start in range(0, len(items), chunk_size):
            chunk = items[start : start + chunk_size]
            results = _groq_categorize_batch(chunk)
            for it in chunk:
                if it["id"] in results:
                    categories[it["id"]] = results[it["id"]]
        for i, it in enumerate(items):
            if categories[i] == UNKNOWN:
                categories[i] = _categorize_merchant_rules(it["merchant"], it["category_hint"])
    else:
        for i, it in enumerate(items):
            categories[i] = _categorize_merchant_rules(it["merchant"], it["category_hint"])

    out["category"] = categories
    return out
