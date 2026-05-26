from datetime import datetime
from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from src.analytics.metrics import AnalyticsSummary
from src.config import REPORTS_DIR


def generate_pdf_report(
    transactions: pd.DataFrame,
    analytics: AnalyticsSummary,
    receipts: pd.DataFrame | None = None,
    output_path: Path | None = None,
) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = output_path or REPORTS_DIR / f"financial_report_{datetime.now():%Y%m%d_%H%M%S}.pdf"

    doc = SimpleDocTemplate(str(path), pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("Financial Intelligence Report", styles["Title"]))
    story.append(Paragraph(f"Generated {datetime.now():%Y-%m-%d %H:%M}", styles["Normal"]))
    story.append(Spacer(1, 0.25 * inch))

    summary_data = [
        ["Metric", "Value"],
        ["Revenue", f"${analytics.revenue:,.2f}"],
        ["Expenses", f"${analytics.expenses:,.2f}"],
        ["Net Cash Flow", f"${analytics.cash_flow:,.2f}"],
        ["Receipts Parsed", str(analytics.receipt_count)],
        ["Receipt Total (extracted)", f"${analytics.receipt_total_spend:,.2f}"],
    ]
    t = Table(summary_data, colWidths=[2.5 * inch, 2 * inch])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a5f")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f4f8")]),
            ]
        )
    )
    story.append(t)
    story.append(Spacer(1, 0.3 * inch))

    if receipts is not None and not receipts.empty:
        story.append(Paragraph("Receipt Intelligence (Gemini)", styles["Heading2"]))
        for _, r in receipts.iterrows():
            merchant = r.get("merchant_raw") or "—"
            amt = r.get("amount")
            amt_s = f"${float(amt):,.2f}" if amt is not None and pd.notna(amt) else "—"
            curr = r.get("currency") or ""
            pay = r.get("payment_method") or ""
            story.append(
                Paragraph(
                    f"{r.get('source_file')}: {merchant} — {amt_s} {curr} ({pay})",
                    styles["Normal"],
                )
            )
        story.append(Spacer(1, 0.2 * inch))

    if analytics.flags:
        story.append(Paragraph("Alerts", styles["Heading2"]))
        for flag in analytics.flags[:15]:
            story.append(Paragraph(f"[{flag['level'].upper()}] {flag['message']}", styles["Normal"]))

    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph("Recent Transactions", styles["Heading2"]))

    display = transactions.head(20).copy()
    for col in ("date", "merchant", "amount", "category", "source"):
        if col not in display.columns:
            display[col] = ""
    display["date"] = display["date"].apply(
        lambda d: pd.Timestamp(d).strftime("%Y-%m-%d") if pd.notna(d) else ""
    )
    rows = [["Date", "Merchant", "Amount", "Category", "Source"]]
    for _, r in display.iterrows():
        amt = r.get("amount")
        amt_str = f"${float(amt):,.2f}" if amt is not None and pd.notna(amt) else ""
        rows.append(
            [
                str(r.get("date", "")),
                str(r.get("merchant", ""))[:30],
                amt_str,
                str(r.get("category", "")),
                str(r.get("source", "")),
            ]
        )
    tx_table = Table(rows, colWidths=[1 * inch, 2 * inch, 1 * inch, 1.2 * inch, 0.8 * inch])
    tx_table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.25, colors.grey)]))
    story.append(tx_table)

    doc.build(story)
    return path
