from __future__ import annotations

from pathlib import Path

import pandas as pd


def parse_invoices(xlsx_path: Path) -> pd.DataFrame:
    df = pd.read_excel(xlsx_path, sheet_name=0)
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]

    col_map: dict[str, str] = {}
    for col in df.columns:
        if "invoice" in col and "id" in col:
            col_map["invoice_id"] = col
        elif col in ("date", "invoice_date", "date_sent", "sent"):
            col_map["date_raw"] = col
        elif "paid" in col and "date" in col:
            col_map["date_paid"] = col
        elif col in ("vendor", "client", "merchant", "customer"):
            col_map["merchant_raw"] = col
        elif col == "description":
            col_map["description"] = col
        elif col in ("amount", "total", "value"):
            col_map["amount"] = col
        elif col == "status":
            col_map["status"] = col

    records = []
    for idx, row in df.iterrows():
        client = str(row.get(col_map.get("merchant_raw", ""), "") or "").strip()
        desc = str(row.get(col_map.get("description", ""), "") or "").strip()
        merchant = client
        if desc and desc.lower() not in client.lower():
            merchant = f"{client} — {desc}" if client else desc

        paid_col = col_map.get("date_paid")
        date_paid = row.get(paid_col) if paid_col else None
        is_paid = pd.notna(date_paid) and str(date_paid).strip().lower() not in ("", "nan", "nat")

        status_col = col_map.get("status")
        if status_col:
            status = str(row.get(status_col, "pending")).lower()
        else:
            status = "paid" if is_paid else "pending"

        inv_id_col = col_map.get("invoice_id")
        invoice_id = str(row.get(inv_id_col, "")) if inv_id_col else f"{xlsx_path.stem}-{idx + 1}"

        records.append(
            {
                "source": "invoice",
                "invoice_id": invoice_id,
                "date_raw": str(row.get(col_map.get("date_raw", ""), "")),
                "merchant_raw": merchant,
                "amount": _to_float(row.get(col_map.get("amount"))),
                "status_raw": status,
                "source_file": xlsx_path.name,
            }
        )
    return pd.DataFrame(records)


def parse_all_invoices(xlsx_paths: list[Path]) -> pd.DataFrame:
    frames = []
    for path in xlsx_paths:
        df = parse_invoices(path)
        if not df.empty:
            frames.append(df)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def _to_float(val) -> float | None:
    if pd.isna(val):
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None
