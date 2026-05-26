from dataclasses import dataclass, field

import pandas as pd


@dataclass
class AnalyticsSummary:
    revenue: float = 0.0
    expenses: float = 0.0
    cash_flow: float = 0.0
    flags: list[dict] = field(default_factory=list)
    by_category: pd.DataFrame = field(default_factory=pd.DataFrame)
    monthly: pd.DataFrame = field(default_factory=pd.DataFrame)
    top_merchants: pd.DataFrame = field(default_factory=pd.DataFrame)
    unreconciled_invoices: int = 0
    receipt_count: int = 0
    receipt_errors: int = 0
    receipt_total_spend: float = 0.0
    payment_methods: pd.DataFrame = field(default_factory=pd.DataFrame)


def _signed_amount(row: pd.Series) -> float:
    amt = row.get("amount")
    if amt is None or pd.isna(amt):
        return 0.0
    val = float(amt)
    cat = str(row.get("category", ""))
    src = row.get("source")
    if cat == "Revenue" or src == "invoice":
        return abs(val)
    if src in ("statement", "receipt"):
        return -abs(val)
    if val > 0 and src == "note":
        return abs(val)
    return -abs(val)


def compute_analytics(
    transactions: pd.DataFrame,
    parsed: dict | None = None,
) -> AnalyticsSummary:
    summary = AnalyticsSummary()
    parsed = parsed or {}

    if transactions.empty:
        summary.flags.append({"level": "error", "message": "No transaction data for analytics."})
        return summary

    df = transactions.copy()
    df["signed_amount"] = df.apply(_signed_amount, axis=1)

    summary.revenue = float(df.loc[df["signed_amount"] > 0, "signed_amount"].sum())
    summary.expenses = float(abs(df.loc[df["signed_amount"] < 0, "signed_amount"].sum()))
    summary.cash_flow = summary.revenue - summary.expenses

    if "category" in df.columns:
        summary.by_category = (
            df.groupby("category", dropna=False)["signed_amount"]
            .sum()
            .reset_index()
            .rename(columns={"signed_amount": "total"})
        )

    if "date" in df.columns and df["date"].notna().any():
        df["month"] = pd.to_datetime(df["date"]).dt.to_period("M").astype(str)
        summary.monthly = (
            df.groupby("month")["signed_amount"]
            .sum()
            .reset_index()
            .rename(columns={"signed_amount": "cash_flow"})
        )

    expenses = df[df["signed_amount"] < 0].copy()
    if not expenses.empty and "merchant" in expenses.columns:
        summary.top_merchants = (
            expenses.groupby("merchant")["signed_amount"]
            .sum()
            .abs()
            .reset_index()
            .rename(columns={"signed_amount": "spend"})
            .sort_values("spend", ascending=False)
            .head(8)
        )

    receipts_df = parsed.get("receipts", pd.DataFrame())
    if not receipts_df.empty:
        summary.receipt_count = len(receipts_df)
        if "ocr_mode" in receipts_df.columns:
            summary.receipt_errors = int((receipts_df["ocr_mode"] == "error").sum())

        valid = receipts_df[
            receipts_df["amount"].apply(lambda a: a is not None and not pd.isna(a) and float(a) > 0)
        ]
        summary.receipt_total_spend = float(valid["amount"].astype(float).sum()) if not valid.empty else 0.0

        missing = receipts_df[
            receipts_df["merchant_raw"].isna()
            | receipts_df["amount"].isna()
            | (receipts_df["ocr_mode"] == "error")
        ]
        for _, row in missing.head(3).iterrows():
            summary.flags.append(
                {
                    "level": "warning",
                    "message": f"Receipt incomplete: {row.get('source_file')} — check image quality",
                }
            )

        pm = receipts_df.get("payment_method")
        if pm is not None:
            pm_clean = pm.dropna().astype(str)
            pm_clean = pm_clean[pm_clean.str.lower() != "none"]
            if not pm_clean.empty:
                counts = pm_clean.value_counts().reset_index()
                counts.columns = ["method", "count"]
                summary.payment_methods = counts

    if "invoice_reconciled" in df.columns:
        inv_sources = df[df["source"] == "invoice"]
        summary.unreconciled_invoices = int((~inv_sources["invoice_reconciled"].fillna(False)).sum())
        if summary.unreconciled_invoices:
            summary.flags.append(
                {
                    "level": "info",
                    "message": f"{summary.unreconciled_invoices} invoice(s) pending reconciliation",
                }
            )

    large = df[df["amount"].apply(lambda a: a is not None and not pd.isna(a) and abs(float(a)) > 500)]
    for _, row in large.iterrows():
        summary.flags.append(
            {
                "level": "info",
                "message": f"Large transaction: {row.get('merchant')} — ${abs(float(row.get('amount'))):,.2f}",
            }
        )

    if summary.cash_flow < 0:
        summary.flags.append(
            {"level": "warning", "message": f"Negative net cash flow: ${summary.cash_flow:,.2f}"}
        )

    if summary.receipt_errors:
        summary.flags.append(
            {
                "level": "error",
                "message": f"{summary.receipt_errors} receipt(s) could not be read by Gemini",
            }
        )

    return summary
