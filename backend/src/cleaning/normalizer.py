import re

import pandas as pd
from dateutil import parser as date_parser

from src.cleaning.entity_names import merchant_group_key
from src.cleaning.status import normalize_payment_status
from src.config import DATE_FORMATS, DEFAULT_CURRENCY


def _normalize_date(val):
    if pd.isna(val) or val == "" or val is None:
        return pd.NaT
    s = str(val).strip()
    for fmt in DATE_FORMATS:
        try:
            return pd.Timestamp(pd.to_datetime(s, format=fmt))
        except (ValueError, TypeError):
            pass
    try:
        return pd.Timestamp(date_parser.parse(s, dayfirst=False))
    except (ValueError, TypeError, OverflowError):
        return pd.NaT


def _normalize_currency_amount(val) -> float | None:
    if pd.isna(val) or val is None:
        return None
    if isinstance(val, (int, float)):
        return round(float(val), 2)
    s = str(val).replace("$", "").replace(",", "").strip()
    if not s:
        return None
    try:
        return round(float(s), 2)
    except ValueError:
        return None


def _clean_merchant(val) -> str:
    if pd.isna(val) or val is None:
        return ""
    s = str(val).strip()
    if s.lower() in ("none", "nan"):
        return ""
    s = re.sub(r"\s+#\d+", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\s{2,}", " ", s)
    return s.title()


def _normalize_iso_currency(val) -> str:
    if pd.isna(val) or not val:
        return DEFAULT_CURRENCY
    return str(val).strip().upper()[:3]


def _dedupe_key(row: pd.Series) -> str:
    date = row.get("date")
    merchant = row.get("merchant", "")
    amount = row.get("amount")
    if pd.isna(date):
        d = "nodate"
    else:
        d = pd.Timestamp(date).strftime("%Y-%m-%d")
    amt = f"{amount:.2f}" if amount is not None and not pd.isna(amount) else "0"
    src = str(row.get("source", "")).lower()
    inv = row.get("invoice_id")
    inv_part = ""
    if src == "invoice" and inv is not None and not pd.isna(inv) and str(inv).strip():
        inv_part = f"|{str(inv).strip()}"
    return f"{src}|{d}|{str(merchant).lower()}|{amt}{inv_part}"


def normalize_transactions(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    out = df.copy()
    out["date"] = out["date_raw"].apply(_normalize_date) if "date_raw" in out.columns else pd.NaT
    out["amount"] = out["amount"].apply(_normalize_currency_amount) if "amount" in out.columns else None
    out["merchant"] = out["merchant_raw"].apply(_clean_merchant) if "merchant_raw" in out.columns else ""
    if "merchant_raw" in out.columns:
        out["merchant_group"] = out["merchant_raw"].apply(merchant_group_key)
    else:
        out["merchant_group"] = out.get("merchant", "")

    out["status"] = out.apply(normalize_payment_status, axis=1)

    if "currency" in out.columns:
        out["currency"] = out["currency"].apply(_normalize_iso_currency)
    else:
        out["currency"] = DEFAULT_CURRENCY

    out["dedupe_key"] = out.apply(_dedupe_key, axis=1)
    out = out.drop_duplicates(subset=["dedupe_key"], keep="first")
    out = out.sort_values("date", na_position="last").reset_index(drop=True)
    return out


def combine_sources(parsed: dict[str, pd.DataFrame]) -> pd.DataFrame:
    frames = []
    for df in parsed.values():
        if df is not None and not df.empty:
            frames.append(df)
    if not frames:
        return pd.DataFrame()
    combined = pd.concat(frames, ignore_index=True, sort=False)
    return normalize_transactions(combined)
