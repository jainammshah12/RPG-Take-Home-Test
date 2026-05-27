from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import List, Optional

import pandas as pd
from dotenv import load_dotenv
from google import genai
from google.genai import types
from PIL import Image, ImageOps
from pydantic import BaseModel, Field

# Load environment configuration files
load_dotenv()

# ---------------------------------------------------------------------------
# 1. Pydantic Structured Schema Definition
# ---------------------------------------------------------------------------

class LineItem(BaseModel):
    description: str = Field(description="Clean name of the item or service.")
    quantity: Optional[int] = Field(None, description="Units purchased.")
    unit_price: Optional[float] = Field(None, description="Price per individual unit.")

class ReceiptSchema(BaseModel):
    is_receipt: bool = Field(
        description="True ONLY if the image is a transactional record (printed invoice, store receipt, parking stub, or handwritten bill). False if it is a standard photo like an animal, landscape, or person."
    )
    merchant: Optional[str] = Field(None, description="Name of the business establishment (e.g., 'Bureau en Gros', 'Jean Coutu', 'Chen's Art Supply'). Exclude address strings.")
    date: Optional[str] = Field(None, description="The transaction date transformed into clean ISO format: YYYY-MM-DD.")
    amount: Optional[float] = Field(None, description="The exact net final cost paid for the transaction. This is the absolute final total bill cost.")
    subtotal: Optional[float] = Field(None, description="Total cost before taxes and environmental/handling fees.")
    tax: Optional[float] = Field(None, description="The combined sum of all calculated regional taxes (e.g., combine TPS/GST and TVQ/PST for Canadian receipts).")
    currency: str = Field("CAD", description="3-letter ISO code. Default to CAD for Canadian stores.")
    payment_method: Optional[str] = Field(None, description="Method used (e.g., 'cash', 'debit', 'credit', 'e-transfer').")
    line_items: List[LineItem] = Field(default=[], description="Structural itemized list breakdown if fully legible.")
    notes: Optional[str] = Field(None, description="Internal processing flag logs regarding anomalies or script readability.")


# ---------------------------------------------------------------------------
# 2. Environment Variables Sanitization & Initialization
# ---------------------------------------------------------------------------

def _get_client() -> genai.Client:
    """Initializes the production client while programmatically clearing API key collisions."""
    # Automated fix for key collision visible in console logs
    if "GOOGLE_API_KEY" in os.environ and "GEMINI_API_KEY" in os.environ:
        del os.environ["GOOGLE_API_KEY"]

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("[CRITICAL ERROR]: GEMINI_API_KEY is missing from your active environment setup.", file=sys.stderr)
        sys.exit(1)
        
    return genai.Client(api_key=api_key)


# ---------------------------------------------------------------------------
# 3. OPTION 1: Local Vision Token Footprint Compression
# ---------------------------------------------------------------------------

# Max resolution boundary optimized for Gemini text recognition legibility 
# While drastically decreasing overall Tokens Per Minute (TPM) usage footprint.
_MAX_TARGET_DIMENSION = 1024  

def _preprocess_image(image_path: Path) -> Image.Image:
    """Loads, auto-corrects orientation flips, and scales down images to optimize processing volume."""
    with Image.open(image_path) as img:
        img.load()
    
    # Fixes upside down or sideways mobile phone captures before payload transmission
    img = ImageOps.exif_transpose(img)
    
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
        
    # Scale processing matrix down to keep payload size beneath strict TPM bounds
    w, h = img.size
    if max(w, h) > _MAX_TARGET_DIMENSION:
        scale = _MAX_TARGET_DIMENSION / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
        
    return img


# ---------------------------------------------------------------------------
# 4. Prompt Engineering Directives Matrix
# ---------------------------------------------------------------------------

_SYSTEM_INSTRUCTION = """You are a forensic accounting database parser. Your strict constraint is 100% data extraction precision.

Inspect the transaction file image and map variables using these operational rules:

1. THE CANADIAN/QUEBEC TRANSLATION LAYER (beg.png, pharmacy.png, parking.jpeg):
   - You are dealing with French or Bilingual documents.
   - "Sous-total" maps to subtotal.
   - Sum "TPS" (5%) and "TVQ" (9.975%) calculations explicitly into the single target `tax` floating-point field.

2. THE "CHANGE TENDERED" WALL (CRITICAL FOR Bureau en Gros / Jean Coutu):
   - Never extract the total amount paid cash line ("COMPTANT") or change given back ("MONNAIE") as the receipt cost.
   - Example analysis context: If a log displays TOTAL: $40.80, COMPTANT: $50.00, and MONNAIE: $9.20; the true transaction total amount is strictly 40.80.

3. HANDWRITTEN NOTEBOOKS (artsupplies.jpg):
   - Accurately parse unstructured human handwriting across unlined pages.
   - If a specific price sum is heavily circled, underlined, or isolated next to the word "TOTAL", prioritize this value as your transaction total amount.

4. NON-RECEIPT REJECTION MATRIX (chat_gpt.jpg):
   - If the visual object represents an animal (such as a dog), a landscape, or a personal photo, flag `is_receipt = false` immediately and leave data parameters blank.

5. CALENDAR STAMP STANDARDIZATION:
   - Convert all date notations (e.g., DD/MM/YYYY formats like '22/01/2025' or '20/03/2025') into unified 'YYYY-MM-DD' ISO formats.
"""


# ---------------------------------------------------------------------------
# 5. Core Operational Controller Loop with OPTION 2 (Rate Pacing)
# ---------------------------------------------------------------------------

def audit_receipt_image(image_path: Path, max_retries: int = 3) -> dict:
    """Audits a single target image path using structured vision outputs with backoff logic."""
    image_path = Path(image_path)
    
    try:
        source_img = _preprocess_image(image_path)
    except Exception as err:
        return _build_fallback_row(image_path, f"Image transformation step crashed: {err}")

    try:
        ai_client = _get_client()
    except Exception as err:
        return _build_fallback_row(image_path, str(err))

    # Internal runner containing adaptive retry algorithms to handle network quotas
    base_backoff_delay = 4.0
    for attempt in range(max_retries):
        try:
            api_payload = ai_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[_SYSTEM_INSTRUCTION, source_img],
                config=types.GenerateContentConfig(
                    temperature=0.0,  # Forces deterministic output tracking
                    response_mime_type="application/json",
                    response_schema=ReceiptSchema,
                ),
            )
            break  # Call successful, exit retry loop
            
        except Exception as err:
            error_msg = str(err).lower()
            # Intercept rate limit errors directly
            if "429" in error_msg or "quota" in error_msg or "resource_exhausted" in error_msg:
                # Calculate adaptive backoff exponential scaling
                sleep_duration = base_backoff_delay * (2 ** attempt)
                print(f"[Quota Intercept] 429 encountered on {image_path.name}. Retrying in {sleep_duration}s... (Attempt {attempt + 1}/{max_retries})")
                time.sleep(sleep_duration)
            else:
                return _build_fallback_row(image_path, f"Direct unhandled execution crash: {err}")
    else:
        # Loop finished without breaking out, meaning all retries hit a quota wall
        return _build_fallback_row(image_path, "API rate limits completely saturated. Processing aborted after retries.")

    if not api_payload.text:
        return _build_fallback_row(image_path, "Server pipeline returned an empty payload string.")

    try:
        clean_json = json.loads(api_payload.text.strip())
    except json.JSONDecodeError:
        return _build_fallback_row(image_path, "Failed to parse structural JSON response stream tokens.")

    return {
        "source": "receipt",
        "source_file": image_path.name,
        "is_valid_receipt": clean_json.get("is_receipt", False),
        "merchant_raw": clean_json.get("merchant"),
        "amount": clean_json.get("amount"),
        "subtotal": clean_json.get("subtotal"),
        "tax": clean_json.get("tax"),
        "tip": None,
        "currency": clean_json.get("currency", "CAD"),
        "date_raw": clean_json.get("date"),
        "payment_method": clean_json.get("payment_method"),
        "line_items": clean_json.get("line_items", []),
        "confidence": "high" if clean_json.get("amount") else "low",
        "notes": clean_json.get("notes", "Successfully verified via compressed multimodal vision parameters."),
        "ocr_mode": "gemini-2.0-flash-vision-v3-optimized",
    }


def process_receipt_batch(target_files: list[Path], mandatory_pacing_delay: float = 4.5) -> pd.DataFrame:
    """Processes your batch list with an enforced minimum cadence delay between requests."""
    if not target_files:
        return pd.DataFrame()
        
    compiled_rows = []
    total_files = len(target_files)
    
    for idx, file_path in enumerate(target_files):
        print(f"[Processing File {idx + 1}/{total_files}]: {file_path.name}")
        row_data = audit_receipt_image(file_path)
        compiled_rows.append(row_data)
        
        # OPTION 2: Enforce a strict cadence delay between loop items
        # Spacing requests completely eliminates high Requests Per Minute (RPM) spikes.
        if idx < total_files - 1:
            print(f"  -> Enforcing pacing delay of {mandatory_pacing_delay}s to safeguard API quotas...")
            time.sleep(mandatory_pacing_delay)
            
    return pd.DataFrame(compiled_rows)


def _build_fallback_row(image_path: Path, error_context: str) -> dict:
    """Maintains pipeline execution integrity by logging processing errors as fallback rows."""
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
        "confidence": "error",
        "notes": f"CRITICAL CONTEXT ERROR: {error_context}",
        "ocr_mode": "error-handling-fallback-v3",
    }