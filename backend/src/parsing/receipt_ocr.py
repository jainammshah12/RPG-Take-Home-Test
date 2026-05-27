from __future__ import annotations
 
import os
from pathlib import Path
 
import pandas as pd
from mindee import ClientV2, InferenceParameters, InferenceResponse, PathInput
 
 
# ---------------------------------------------------------------------------
# Config — read from environment variables
# ---------------------------------------------------------------------------
 
def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise EnvironmentError(
            f"{name} is not set.\n"
            "See the setup instructions at the top of this file."
        )
    return value
 
 
# ---------------------------------------------------------------------------
# Field extraction helpers
# ---------------------------------------------------------------------------
 
def _str(fields: dict, key: str) -> str | None:
    """Safely get a simple string field value."""
    try:
        return fields[key].value
    except (KeyError, AttributeError):
        return None
 
 
def _float(fields: dict, key: str) -> float | None:
    """Safely get a simple numeric field value."""
    try:
        val = fields[key].value
        return float(val) if val is not None else None
    except (KeyError, AttributeError, TypeError, ValueError):
        return None
 
 
def _locale_currency(fields: dict) -> str:
    """Extract currency from the nested locale field, default to CAD."""
    try:
        subfields = fields["locale"].value  # ObjectField
        return subfields.get("currency") or "CAD"
    except (KeyError, AttributeError, TypeError):
        return "CAD"
 
 
def _taxes(fields: dict) -> float | None:
    """Sum all individual tax amounts into a single total tax figure."""
    try:
        tax_list = fields["taxes"].value  # ListField of ObjectFields
        if not tax_list:
            return None
        total = sum(
            float(t.get("amount") or 0)
            for t in tax_list
            if t.get("amount") is not None
        )
        return round(total, 2) if total else None
    except (KeyError, AttributeError, TypeError):
        return None
 
 
def _line_items(fields: dict) -> list[dict]:
    """Extract line items as a list of plain dicts."""
    try:
        items = fields["line_items"].value  # ListField
        if not items:
            return []
        return [
            {
                "description": item.get("description"),
                "quantity": item.get("quantity"),
                "unit_price": item.get("unit_price"),
                "total_price": item.get("total_price"),
            }
            for item in items
        ]
    except (KeyError, AttributeError, TypeError):
        return []
 
 
def _payment_method(fields: dict) -> str | None:
    """Mindee doesn't have a dedicated payment_method field; derive from notes."""
    # Financial Document model doesn't extract payment method directly.
    # We leave it None — extend here if you add a custom field in Mindee's schema.
    return None
 
 
# ---------------------------------------------------------------------------
# Core parsing
# ---------------------------------------------------------------------------
 
def parse_receipt(image_path: Path) -> dict:
    """
    Parse a single receipt/invoice image using the Mindee Financial Document API.
    Returns a flat dict matching your required schema.
    """
    image_path = Path(image_path)
 
    api_key = _require_env("MINDEE_API_KEY")
    model_id = _require_env("MINDEE_MODEL_ID")
 
    client = ClientV2(api_key)
 
    params = InferenceParameters(
        model_id=model_id,
        rag=None,        # enable RAG for better accuracy on complex docs (costs more quota)
        confidence=True, # include confidence scores
        polygon=False,
        raw_text=False,
    )
 
    try:
        input_source = PathInput(str(image_path))
        response: InferenceResponse = client.enqueue_and_get_result(
            InferenceResponse,
            input_source,
            params,
        )
    except Exception as exc:
        return _error_record(image_path, str(exc))
 
    try:
        fields: dict = response.inference.result.fields
    except AttributeError as exc:
        return _error_record(image_path, f"Unexpected response shape: {exc}")
 
    amount   = _float(fields, "total_amount")
    subtotal = _float(fields, "total_net")
    tax      = _taxes(fields)
    date_raw = _str(fields, "date")
    merchant = _str(fields, "supplier_name")
    doc_type = _str(fields, "document_type")  # "receipt", "invoice", etc.
 
    return {
        "source": "receipt",
        "source_file": image_path.name,
        "is_valid_receipt": doc_type in ("receipt", "invoice", None),  # None = model uncertain but parsed
        "merchant_raw": merchant,
        "amount": amount,
        "subtotal": subtotal,
        "tax": tax,
        "tip": None,  # not a Mindee field
        "currency": _locale_currency(fields),
        "date_raw": date_raw,
        "payment_method": _payment_method(fields),
        "line_items": _line_items(fields),
        "confidence": "high" if amount is not None else "low",
        "notes": f"document_type={doc_type}",
        "ocr_mode": f"mindee-financial-document ({model_id})",
    }
 
 
def parse_receipts(receipt_paths: list[Path]) -> pd.DataFrame:
    """Parse multiple receipt images; returns a tidy DataFrame."""
    if not receipt_paths:
        return pd.DataFrame(columns=[
            "source", "source_file", "is_valid_receipt", "merchant_raw",
            "amount", "subtotal", "tax", "tip", "currency", "date_raw",
            "payment_method", "line_items", "confidence", "notes", "ocr_mode",
        ])
    rows = [parse_receipt(p) for p in receipt_paths]
    return pd.DataFrame(rows)
 
 
# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
 
def _error_record(image_path: Path, message: str) -> dict:
    return {
        "source": "receipt",
        "source_file": image_path.name,
        "is_valid_receipt": False,
        "merchant_raw": None,
        "amount": None,
        "subtotal": None,
        "tax": None,
        "tip": None,
        "currency": "CAD",
        "date_raw": None,
        "payment_method": None,
        "line_items": [],
        "confidence": "low",
        "notes": f"ERROR: {message}",
        "ocr_mode": "error",
    }