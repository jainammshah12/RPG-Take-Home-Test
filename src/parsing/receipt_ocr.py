from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import List, Optional

import pandas as pd
from dotenv import load_dotenv
from google import genai
from google.genai import types
from PIL import Image, ImageOps
from pydantic import BaseModel, Field

load_dotenv()

# ---------------------------------------------------------------------------
# 1. Response Schemas (Guarantees JSON Structure)
# ---------------------------------------------------------------------------

class LineItem(BaseModel):
    description: str = Field(description="The name or description of the product or service.")
    quantity: Optional[int] = Field(None, description="The number of items purchased.")
    unit_price: Optional[float] = Field(None, description="The price per single item.")

class ReceiptSchema(BaseModel):
    is_receipt: bool = Field(
        description="True if the image is a valid transaction receipt, invoice, bill, parking stub, or handwritten sales note. False if it is a photo of a dog, landscape, or completely unrelated object."
    )
    merchant: Optional[str] = Field(None, description="The company or store name (e.g., 'Bureau en Gros', 'Jean Coutu'). Use the most prominent header text if unclear. Do not use addresses.")
    date: Optional[str] = Field(None, description="The transaction date normalized strictly to ISO format: YYYY-MM-DD.")
    amount: Optional[float] = Field(None, description="The absolute final grand total paid by the customer (after all taxes, item deductions, and tips).")
    subtotal: Optional[float] = Field(None, description="The total cost of items BEFORE taxes and fees are added.")
    tax: Optional[float] = Field(None, description="The combined total of all taxes applied (e.g., sum up TPS and TVQ for Quebec receipts).")
    tip: Optional[float] = Field(None, description="Any added tip or gratuity amount.")
    currency: Optional[str] = Field("CAD", description="3-letter ISO currency code. Infer from address or symbols (e.g., CAD, USD, EUR).")
    line_items: List[LineItem] = Field(default=[], description="List of individual items purchased.")
    payment_method: Optional[str] = Field(None, description="The payment type used (e.g., 'cash', 'debit', 'credit', 'e-transfer').")
    confidence: str = Field(description="Set to 'high', 'medium', or 'low' based on how legible the image text is.")
    notes: Optional[str] = Field(None, description="Brief extraction notes, such as unreadable handwriting or language issues.")


# ---------------------------------------------------------------------------
# 2. Client Initialization
# ---------------------------------------------------------------------------

def _get_client() -> genai.Client:
    # Explicitly isolate the correct AI Studio key
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError("GEMINI_API_KEY is not set.")
        
    os.environ.pop("GOOGLE_API_KEY", None)
    
    return genai.Client(api_key=api_key)


_MODEL = "gemini-2.0-flash" 


# ---------------------------------------------------------------------------
# 3. Upgraded Image Loader (Fixes Sideways Mobile Photos)
# ---------------------------------------------------------------------------

_MAX_DIMENSION = 1568  

def _load_image(image_path: Path) -> Image.Image:
    """Load image, automatically fix EXIF orientation, resize if oversized, convert to RGB."""
    with Image.open(image_path) as img:
        img.load()  

    # CRITICAL: This transposes the image pixels based on the camera's original orientation
    img = ImageOps.exif_transpose(img)

    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    w, h = img.size
    if max(w, h) > _MAX_DIMENSION:
        scale = _MAX_DIMENSION / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    return img


# ---------------------------------------------------------------------------
# 4. Optimized Prompt
# ---------------------------------------------------------------------------

_PROMPT = """You are an advanced multilingual financial OCR vision engine.

Analyze the provided image carefully to determine if it is a transaction record, and then extract the data to match the required JSON schema.

SPECIAL INSTRUCTIONS:
1. VALIDITY CHECK: First verify if the image is a valid transaction record (receipt, invoice, hand-written note, bill). If it's an image of a dog, animal, or random non-receipt object, immediately set `is_receipt` to false and leave financial fields null.
2. MULTILINGUAL & HANDWRITTEN CONTEXT: Receipts may contain handwritten text or be entirely in French (e.g., look for 'Sous-total', 'TPS', 'TVQ', 'Comptant', 'Stationnement'). 
3. CRITICAL TOTAL VALUE: Look for the ultimate final bottom-line amount paid. Do not mistake the 'Subtotal' or cash 'Tendered/Comptant' values for the final amount.
4. DATE NORMALIZATION: Convert dates to ISO standard YYYY-MM-DD. Be aware of standard Canadian/Quebec formatting variants (e.g., DD/MM/YYYY vs MM/DD/YYYY).
"""


# ---------------------------------------------------------------------------
# 5. Core Parsing Execution
# ---------------------------------------------------------------------------

def parse_receipt(image_path: Path) -> dict:
    """
    Parse a single receipt image using Gemini structured generation.
    Returns a normalized dictionary.
    """
    image_path = Path(image_path)

    try:
        img = _load_image(image_path)
    except Exception as exc:
        return _error_record(image_path, f"Image load failed: {exc}")

    client = _get_client()

    # Wrapped generation request with structural enforcement
    def _call_api():
        return client.models.generate_content(
            model=_MODEL,
            contents=[_PROMPT, img],
            config=types.GenerateContentConfig(
                temperature=0.0,  # Zero out creativity for strict OCR extraction
                response_mime_type="application/json",
                response_schema=ReceiptSchema,  # Forces Gemini to output matching structural fields
            ),
        )

    try:
        response = _call_api()
    except Exception as exc:
        # Gracefully catch API/Quota limits (429), wait, and retry once
        if "429" in str(exc) or "quota" in str(exc).lower():
            print(f"Quota hit for {image_path.name}. Sleeping for 2s...")
            time.sleep(2)
            try:
                response = _call_api()
            except Exception as exc2:
                return _error_record(image_path, f"API error after retry: {exc2}")
        else:
            return _error_record(image_path, f"API error: {exc}")

    raw_text = response.text.strip() if response.text else ""

    try:
        # Structured output means Gemini returns guaranteed raw JSON string — no regex parsing needed
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        return _error_record(image_path, f"JSON parse failed. Raw text output: {raw_text[:300]}")

    # Build consistent output format matching your original pipeline
    return {
        "source": "receipt",
        "source_file": image_path.name,
        "is_valid_receipt": parsed.get("is_receipt", False),
        "merchant_raw": parsed.get("merchant"),
        "amount": parsed.get("amount"),
        "subtotal": parsed.get("subtotal"),
        "tax": parsed.get("tax"),
        "tip": parsed.get("tip"),
        "currency": parsed.get("currency", "CAD"),
        "date_raw": parsed.get("date"),
        "payment_method": parsed.get("payment_method"),
        "line_items": parsed.get("line_items", []),
        "confidence": parsed.get("confidence", "low"),
        "notes": parsed.get("notes"),
        "ocr_mode": f"gemini-vision-structured ({_MODEL})",
    }


def parse_receipts(receipt_paths: list[Path]) -> pd.DataFrame:
    """Parse a batch of receipt images and compile them into a pandas DataFrame."""
    if not receipt_paths:
        return pd.DataFrame()
    rows = [parse_receipt(p) for p in receipt_paths]
    return pd.DataFrame(rows)


def _error_record(image_path: Path, message: str) -> dict:
    """Fallback standard record format for ingestion failures."""
    return {
        "source": "receipt",
        "source_file": image_path.name,
        "is_valid_receipt": False,
        "merchant_raw": None,
        "amount": None,
        "subtotal": None,
        "tax": None,
        "tip": None,
        "currency": None,
        "date_raw": None,
        "payment_method": None,
        "line_items": [],
        "confidence": "low",
        "notes": f"ERROR: {message}",
        "ocr_mode": "error",
    }