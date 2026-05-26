import pandas as pd
from rapidfuzz import fuzz, process

from src.config import FUZZY_MATCH_THRESHOLD


def _best_match(query: str, choices: list[str]) -> tuple[str | None, float]:
    if not query or not choices:
        return None, 0.0
    result = process.extractOne(
        query,
        choices,
        scorer=fuzz.token_set_ratio,
    )
    if result is None:
        return None, 0.0
    match, score, _ = result
    if score >= FUZZY_MATCH_THRESHOLD:
        return match, float(score)
    return None, float(score)


def _valid_receipt(row: pd.Series) -> bool:
    if str(row.get("ocr_mode", "")).lower() == "error":
        return False
    merchant = row.get("merchant_raw")
    if merchant is None or (isinstance(merchant, float) and pd.isna(merchant)):
        return False
    if str(merchant).strip().lower() in ("", "none", "nan"):
        return False
    return True


def match_receipts_to_statement(
    transactions: pd.DataFrame,
    receipts: pd.DataFrame,
) -> pd.DataFrame:
    out = transactions.copy()
    out["receipt_matched"] = False
    out["match_score"] = None
    out["matched_receipt_file"] = None
    out["matched_payment_method"] = None

    if receipts.empty or out.empty:
        return out

    receipt_rows = receipts[receipts.apply(_valid_receipt, axis=1)].copy()
    if receipt_rows.empty:
        return out

    stmt_mask = out["source"] == "statement"
    statement_merchants = out.loc[stmt_mask, "merchant"].astype(str).tolist()

    for _, rec in receipt_rows.iterrows():
        merchant = _clean_merchant_for_match(rec.get("merchant_raw"))
        amount = rec.get("amount")

        match_name, score = _best_match(merchant, statement_merchants)
        if not match_name:
            continue

        candidates = out[stmt_mask & (out["merchant"] == match_name)]
        if amount is not None and not pd.isna(amount):
            amt = abs(float(amount))
            amount_match = candidates[
                candidates["amount"].apply(
                    lambda a: a is not None
                    and not pd.isna(a)
                    and abs(abs(float(a)) - amt) < 0.01
                )
            ]
            if not amount_match.empty:
                candidates = amount_match

        if candidates.empty:
            continue

        target_idx = candidates.index[0]
        out.loc[target_idx, "receipt_matched"] = True
        out.loc[target_idx, "match_score"] = score
        out.loc[target_idx, "matched_receipt_file"] = rec.get("source_file")
        out.loc[target_idx, "matched_payment_method"] = rec.get("payment_method")

    return out


def _clean_merchant_for_match(val) -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    s = str(val).strip()
    return s.title()
