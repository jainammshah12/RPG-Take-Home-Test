import pandas as pd

from src.config import MERCHANT_CATEGORIES


def categorize(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    out = df.copy()

    def _category(row: pd.Series) -> str:
        hint = str(row.get("category_hint", "") or "").strip()
        if hint:
            return hint
        merchant = str(row.get("merchant", "")).lower()
        for keyword, cat in MERCHANT_CATEGORIES.items():
            if keyword in merchant:
                return cat
        src = str(row.get("source", ""))
        amount = row.get("amount")
        if src == "invoice":
            return "Revenue"
        if amount is not None and not pd.isna(amount) and float(amount) > 0:
            if src == "note" and any(k in merchant for k in ("refund", "paid", "payment")):
                return "Revenue"
        if amount is not None and not pd.isna(amount) and float(amount) < 0:
            return "Expense"
        if src in ("statement", "receipt"):
            return "Expense"
        return "Uncategorized"

    out["category"] = out.apply(_category, axis=1)
    return out
