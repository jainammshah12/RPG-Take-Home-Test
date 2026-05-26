import pandas as pd


def reconcile_invoices(
    transactions: pd.DataFrame,
    invoices: pd.DataFrame,
) -> pd.DataFrame:
    out = transactions.copy()
    out["invoice_reconciled"] = False
    out["invoice_id"] = out.get("invoice_id", pd.Series(dtype=object))

    if invoices.empty:
        return out

    inv = invoices.copy()
    inv["amount"] = inv["amount"].apply(lambda a: abs(float(a)) if a is not None and not pd.isna(a) else None)

    for _, inv_row in inv.iterrows():
        inv_amt = inv_row.get("amount")
        inv_merchant = str(inv_row.get("merchant", inv_row.get("merchant_raw", ""))).lower()
        inv_date = inv_row.get("date")

        mask = out["source"].isin(["statement", "note", "receipt"])
        if inv_amt is not None:
            mask &= out["amount"].apply(
                lambda a: a is not None
                and not pd.isna(a)
                and abs(abs(float(a)) - inv_amt) < 0.01
            )
        candidates = out[mask]
        for idx, row in candidates.iterrows():
            if inv_merchant in str(row.get("merchant", "")).lower():
                out.loc[idx, "invoice_reconciled"] = True
                out.loc[idx, "invoice_id"] = inv_row.get("invoice_id", "")
                break

    return out
