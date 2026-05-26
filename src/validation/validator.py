from dataclasses import dataclass, field

import pandas as pd
from pydantic import BaseModel, ValidationError


class TransactionRecord(BaseModel):
    source: str
    merchant: str = ""
    amount: float | None = None
    date: str | None = None
    category: str = "Uncategorized"
    currency: str = "CAD"


@dataclass
class ValidationResult:
    valid: bool = False
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    row_count: int = 0
    display_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    receipt_errors: int = 0


def validate(transactions: pd.DataFrame) -> ValidationResult:
    result = ValidationResult()
    if transactions.empty:
        result.valid = False
        result.errors.append("No transactions to validate.")
        return result

    result.row_count = len(transactions)
    display = transactions.copy()

    for col in ("date", "amount", "merchant", "category", "source", "currency"):
        if col not in display.columns:
            display[col] = None

    if display["amount"].isna().all():
        result.warnings.append("All amounts are missing.")

    if "ocr_mode" in transactions.columns:
        result.receipt_errors = int((transactions["ocr_mode"] == "error").sum())
        if result.receipt_errors:
            result.warnings.append(
                f"{result.receipt_errors} receipt(s) failed Gemini extraction — check GEMINI_API_KEY and images."
            )

    receipt_rows = transactions[transactions["source"] == "receipt"] if "source" in transactions.columns else pd.DataFrame()
    if not receipt_rows.empty and receipt_rows["merchant"].eq("").all():
        result.warnings.append("Receipt merchants could not be resolved from any image.")

    invalid_dates = display["date"].isna().sum()
    if invalid_dates > 0:
        result.warnings.append(f"{invalid_dates} row(s) have unparseable dates.")

    for idx, row in display.iterrows():
        try:
            date_val = row.get("date")
            date_str = None
            if pd.notna(date_val):
                date_str = pd.Timestamp(date_val).strftime("%Y-%m-%d")
            TransactionRecord(
                source=str(row.get("source", "")),
                merchant=str(row.get("merchant", "")),
                amount=row.get("amount") if pd.notna(row.get("amount")) else None,
                date=date_str,
                category=str(row.get("category", "Uncategorized")),
                currency=str(row.get("currency", "CAD")),
            )
        except ValidationError as e:
            result.errors.append(f"Row {idx}: {e}")

    display["date"] = display["date"].apply(
        lambda d: pd.Timestamp(d).strftime("%Y-%m-%d") if pd.notna(d) else ""
    )
    display["amount"] = display["amount"].apply(
        lambda a: f"${a:,.2f}" if a is not None and pd.notna(a) else ""
    )

    result.display_df = display
    result.valid = len(result.errors) == 0
    return result
