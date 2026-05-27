"""Convert pipeline results to JSON-safe structures for the REST API."""

from __future__ import annotations

import math
from typing import Any

import pandas as pd

from src.cache.analysis_store import AnalysisLoadResult
from src.pipeline import PipelineResult


def _json_value(val: Any) -> Any:
    if val is None:
        return None
    if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
        return None
    if isinstance(val, (pd.Timestamp,)):
        return val.strftime("%Y-%m-%d")
    if hasattr(val, "item"):
        try:
            return val.item()
        except (ValueError, AttributeError):
            pass
    if isinstance(val, (list, dict, str, int, float, bool)):
        return val
    return str(val)


def df_to_records(df: pd.DataFrame | None) -> list[dict]:
    if df is None or df.empty:
        return []
    records = []
    for row in df.to_dict(orient="records"):
        records.append({k: _json_value(v) for k, v in row.items()})
    return records


def serialize_analytics(a) -> dict:
    if a is None:
        return {}
    return {
        "revenue": a.revenue,
        "expenses": a.expenses,
        "cash_flow": a.cash_flow,
        "flags": a.flags,
        "monthly": df_to_records(a.monthly),
        "monthly_card_spend": df_to_records(a.monthly_card_spend),
        "by_source": df_to_records(a.by_source),
        "top_merchants": df_to_records(a.top_merchants),
        "top_revenue_clients": df_to_records(a.top_revenue_clients),
        "invoice_status": df_to_records(a.invoice_status),
        "spend_by_category": df_to_records(a.spend_by_category),
        "receipt_count": a.receipt_count,
        "receipt_errors": a.receipt_errors,
        "receipt_total_spend": a.receipt_total_spend,
        "statement_tx_count": a.statement_tx_count,
        "invoice_count": a.invoice_count,
        "invoice_paid_amount": a.invoice_paid_amount,
        "invoice_pending_amount": a.invoice_pending_amount,
    }


def serialize_validation(v) -> dict:
    if v is None:
        return {"valid": False, "errors": [], "warnings": [], "row_count": 0}
    return {
        "valid": v.valid,
        "errors": v.errors,
        "warnings": v.warnings,
        "row_count": v.row_count,
        "receipt_errors": v.receipt_errors,
    }


def serialize_pipeline_result(
    result: PipelineResult,
    *,
    chat_context: str = "",
    signature: str = "",
    load_meta: AnalysisLoadResult | None = None,
) -> dict:
    parsed = {key: df_to_records(result.parsed.get(key)) for key in ("receipts", "statement", "invoices", "notes")}
    return {
        "analytics": serialize_analytics(result.analytics),
        "transactions": df_to_records(result.transactions),
        "parsed": parsed,
        "validation": serialize_validation(result.validation),
        "chat_context": chat_context,
        "signature": signature,
        "meta": {
            "from_disk": load_meta.from_disk if load_meta else False,
            "parsed_new_files": load_meta.parsed_new_files if load_meta else 0,
        },
    }
