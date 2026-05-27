from dataclasses import dataclass, field

import pandas as pd


@dataclass
class AnalyticsSummary:
    revenue: float = 0.0
    expenses: float = 0.0
    cash_flow: float = 0.0
    flags: list[dict] = field(default_factory=list)

    # High-coverage visualizations (≥90% populated in typical shoebox data)
    monthly: pd.DataFrame = field(default_factory=pd.DataFrame)
    monthly_card_spend: pd.DataFrame = field(default_factory=pd.DataFrame)
    by_source: pd.DataFrame = field(default_factory=pd.DataFrame)
    top_merchants: pd.DataFrame = field(default_factory=pd.DataFrame)
    top_revenue_clients: pd.DataFrame = field(default_factory=pd.DataFrame)
    invoice_status: pd.DataFrame = field(default_factory=pd.DataFrame)
    spend_by_category: pd.DataFrame = field(default_factory=pd.DataFrame)

    # Counts & receipt rollup
    receipt_count: int = 0
    receipt_errors: int = 0
    receipt_total_spend: float = 0.0
    statement_tx_count: int = 0
    invoice_count: int = 0
    invoice_paid_amount: float = 0.0
    invoice_pending_amount: float = 0.0


def _signed_amount(row: pd.Series) -> float:
    amt = row.get("amount")
    if amt is None or pd.isna(amt):
        return 0.0
    val = float(amt)
    src = row.get("source")
    if src == "invoice":
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

    # --- By source (100% have `source`) ---
    if "source" in df.columns:
        rows = []
        for src, grp in df.groupby("source"):
            inflow = float(grp.loc[grp["signed_amount"] > 0, "signed_amount"].sum())
            outflow = float(abs(grp.loc[grp["signed_amount"] < 0, "signed_amount"].sum()))
            rows.append(
                {
                    "source": src,
                    "count": len(grp),
                    "inflow": inflow,
                    "outflow": outflow,
                    "net": inflow - outflow,
                }
            )
        summary.by_source = pd.DataFrame(rows)

    summary.statement_tx_count = int((df["source"] == "statement").sum()) if "source" in df.columns else 0

    # --- Monthly cash flow (96%+ have dates) ---
    dated = df[df["date"].notna()].copy() if "date" in df.columns else pd.DataFrame()
    if not dated.empty:
        dated["month"] = pd.to_datetime(dated["date"]).dt.to_period("M").astype(str)
        summary.monthly = (
            dated.groupby("month")["signed_amount"]
            .sum()
            .reset_index()
            .rename(columns={"signed_amount": "cash_flow"})
        )

        stmt = dated[dated["source"] == "statement"]
        if not stmt.empty:
            summary.monthly_card_spend = (
                stmt.groupby("month")["signed_amount"]
                .sum()
                .abs()
                .reset_index()
                .rename(columns={"signed_amount": "card_spend"})
            )

    # --- Spend by accounting category (expense rows with a category) ---
    if "category" in df.columns:
        exp_cats = df[(df["signed_amount"] < 0) & df["category"].notna()].copy()
        if not exp_cats.empty:
            summary.spend_by_category = (
                exp_cats.groupby("category")["signed_amount"]
                .sum()
                .abs()
                .reset_index()
                .rename(columns={"signed_amount": "spend"})
                .sort_values("spend", ascending=False)
            )

    # --- Top merchants by card spend (grouped by brand/client key) ---
    expenses = df[(df["signed_amount"] < 0) & df["merchant"].astype(str).str.len().gt(0)].copy()
    if not expenses.empty:
        group_col = "merchant_group" if "merchant_group" in expenses.columns else "merchant"
        summary.top_merchants = (
            expenses.groupby(group_col)["signed_amount"]
            .sum()
            .abs()
            .reset_index()
            .rename(columns={group_col: "merchant", "signed_amount": "spend"})
            .sort_values("spend", ascending=False)
            .head(10)
        )

    # --- Invoice status & top clients (from unified ledger) ---
    inv_tx = df[df["source"] == "invoice"] if "source" in df.columns else pd.DataFrame()
    if not inv_tx.empty:
        summary.invoice_count = len(inv_tx)
        if "status" in inv_tx.columns and "amount" in inv_tx.columns:
            status_rows = []
            for status, grp in inv_tx.groupby(inv_tx["status"].fillna("Unknown")):
                status_rows.append(
                    {
                        "status": str(status),
                        "count": len(grp),
                        "amount": float(grp["amount"].astype(float).sum()),
                    }
                )
            summary.invoice_status = pd.DataFrame(status_rows)

            paid = inv_tx[inv_tx["status"] == "Paid"]
            pending = inv_tx[inv_tx["status"] == "Pending"]
            summary.invoice_paid_amount = float(paid["amount"].sum()) if not paid.empty else 0.0
            summary.invoice_pending_amount = float(pending["amount"].sum()) if not pending.empty else 0.0

        group_col = "merchant_group" if "merchant_group" in inv_tx.columns else "merchant"
        valid = inv_tx[inv_tx[group_col].astype(str).str.len().gt(0) & inv_tx["amount"].notna()]
        if not valid.empty:
            summary.top_revenue_clients = (
                valid.groupby(group_col)["amount"]
                .sum()
                .reset_index()
                .rename(columns={group_col: "client", "amount": "revenue"})
                .sort_values("revenue", ascending=False)
                .head(8)
            )

    # --- Receipts rollup ---
    receipts_df = parsed.get("receipts", pd.DataFrame())
    if not receipts_df.empty:
        summary.receipt_count = len(receipts_df)
        if "ocr_mode" in receipts_df.columns:
            summary.receipt_errors = int((receipts_df["ocr_mode"] == "error").sum())

        if "amount" in receipts_df.columns:
            valid = receipts_df[
                receipts_df["amount"].apply(
                    lambda a: a is not None and not pd.isna(a) and float(a) > 0
                )
            ]
            summary.receipt_total_spend = (
                float(valid["amount"].astype(float).sum()) if not valid.empty else 0.0
            )

        if "merchant_raw" in receipts_df.columns:
            bad = receipts_df[
                receipts_df["merchant_raw"].isna() | receipts_df["amount"].isna()
            ]
            for _, row in bad.head(2).iterrows():
                summary.flags.append(
                    {
                        "level": "warning",
                        "message": f"Receipt incomplete: {row.get('source_file')}",
                    }
                )

    large = df[df["amount"].apply(lambda a: a is not None and not pd.isna(a) and abs(float(a)) > 500)]
    for _, row in large.head(5).iterrows():
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
                "message": f"{summary.receipt_errors} receipt(s) failed to parse",
            }
        )

    return summary
