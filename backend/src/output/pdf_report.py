from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from src.analytics.metrics import AnalyticsSummary
from src.config import REPORTS_DIR

# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------

_NAVY      = colors.HexColor("#1e3a5f")
_TEAL      = colors.HexColor("#2a9d8f")
_LIGHT_ROW = colors.HexColor("#f5f8fb")
_MID_GREY  = colors.HexColor("#d0d7e2")
_RED       = colors.HexColor("#c0392b")
_GREEN     = colors.HexColor("#27ae60")
_TEXT      = colors.HexColor("#1a1a2e")

PAGE_W = letter[0]

# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------

def _build_styles():
    base = getSampleStyleSheet()

    title = ParagraphStyle(
        "LLTitle",
        parent=base["Normal"],
        fontName="Helvetica-Bold",
        fontSize=22,
        textColor=_NAVY,
        spaceAfter=2,
    )
    subtitle = ParagraphStyle(
        "LLSubtitle",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=9,
        textColor=colors.HexColor("#6b7280"),
        spaceAfter=0,
    )
    section = ParagraphStyle(
        "LLSection",
        parent=base["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        textColor=_NAVY,
        spaceBefore=14,
        spaceAfter=6,
    )
    note = ParagraphStyle(
        "LLNote",
        parent=base["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=8,
        textColor=colors.HexColor("#6b7280"),
    )
    alert_high = ParagraphStyle(
        "LLAlertHigh",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=8,
        textColor=_RED,
        leftIndent=8,
        spaceAfter=2,
    )
    alert_low = ParagraphStyle(
        "LLAlertLow",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=8,
        textColor=colors.HexColor("#b45309"),
        leftIndent=8,
        spaceAfter=2,
    )
    return dict(
        title=title, subtitle=subtitle, section=section,
        note=note, alert_high=alert_high, alert_low=alert_low,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt_amount(val, currency: str = "CAD") -> str:
    try:
        f = float(val)
        return f"${f:,.2f} {currency}"
    except (TypeError, ValueError):
        return "—"


def _divider(story):
    story.append(Spacer(1, 0.08 * inch))
    story.append(HRFlowable(width="100%", thickness=0.5, color=_MID_GREY))
    story.append(Spacer(1, 0.08 * inch))


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------

def _summary_table(analytics: AnalyticsSummary) -> Table:
    """Two-column KPI grid — kept from original, polished styling."""
    cf = analytics.cash_flow
    cf_str = f"${cf:,.2f}" if cf >= 0 else f"(${abs(cf):,.2f})"
    cf_color = _GREEN if cf >= 0 else _RED

    data = [
        ["Revenue",           f"${analytics.revenue:,.2f}"],
        ["Expenses",          f"${analytics.expenses:,.2f}"],
        ["Net Cash Flow",     cf_str],
        ["Card Transactions", str(analytics.statement_tx_count)],
        ["Invoices Paid",     f"${analytics.invoice_paid_amount:,.2f}"],
        ["Invoices Pending",  f"${analytics.invoice_pending_amount:,.2f}"],
        ["Receipts Parsed",   str(analytics.receipt_count)],
    ]

    col_w = [2.8 * inch, 2.0 * inch]
    t = Table(data, colWidths=col_w, hAlign="LEFT")
    style = [
        # outer border
        ("BOX",         (0, 0), (-1, -1), 0.75, _NAVY),
        # internal grid
        ("LINEBELOW",   (0, 0), (-1, -2), 0.3, _MID_GREY),
        # alternating rows
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, _LIGHT_ROW]),
        # text
        ("FONTNAME",    (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME",    (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE",    (0, 0), (-1, -1), 9),
        ("TEXTCOLOR",   (0, 0), (-1, -1), _TEXT),
        ("TOPPADDING",  (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        # highlight cash flow row (index 2)
        ("TEXTCOLOR",   (1, 2), (1, 2), cf_color),
        ("FONTNAME",    (1, 2), (1, 2), "Helvetica-Bold"),
    ]
    t.setStyle(TableStyle(style))
    return t


def _receipt_table(receipts: pd.DataFrame) -> Table | None:
    """
    Focused receipt table: merchant | date | amount | currency | payment.
    Shows up to 30 rows; drops rows with no merchant AND no amount.
    """
    keep_cols = ["merchant_raw", "date_raw", "amount", "currency", "payment_method"]
    df = receipts.copy()
    for c in keep_cols:
        if c not in df.columns:
            df[c] = None

    df = df[keep_cols].dropna(subset=["merchant_raw", "amount"], how="all").head(30)
    if df.empty:
        return None

    header = ["Merchant", "Date", "Amount", "Currency", "Payment"]
    rows = [header]
    for _, r in df.iterrows():
        amt = r.get("amount")
        rows.append([
            str(r.get("merchant_raw") or "—")[:32],
            str(r.get("date_raw") or "—"),
            f"${float(amt):,.2f}" if pd.notna(amt) and amt is not None else "—",
            str(r.get("currency") or "CAD"),
            str(r.get("payment_method") or "—").title(),
        ])

    col_w = [2.1 * inch, 0.9 * inch, 0.85 * inch, 0.75 * inch, 0.85 * inch]
    t = Table(rows, colWidths=col_w, hAlign="LEFT")
    t.setStyle(TableStyle([
        # header row
        ("BACKGROUND",    (0, 0), (-1, 0), _TEAL),
        ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 8),
        # data rows
        ("FONTNAME",      (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",      (0, 1), (-1, -1), 8),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, _LIGHT_ROW]),
        ("TEXTCOLOR",     (0, 1), (-1, -1), _TEXT),
        ("GRID",          (0, 0), (-1, -1), 0.3, _MID_GREY),
        ("BOX",           (0, 0), (-1, -1), 0.6, _NAVY),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        # right-align amount column
        ("ALIGN",         (2, 0), (2, -1), "RIGHT"),
        ("ALIGN",         (3, 0), (3, -1), "CENTER"),
    ]))
    return t


def _transaction_table(transactions: pd.DataFrame) -> Table | None:
    """
    Top-20 transactions by absolute amount.
    Columns: date | merchant | category | amount | currency | source.
    Skips the full dump — shows only what matters.
    """
    cols = ["date", "merchant", "category", "amount", "currency", "source"]
    df = transactions.copy()
    for c in cols:
        if c not in df.columns:
            df[c] = None

    # Sort by absolute amount descending — most significant transactions first
    df["_abs"] = df["amount"].apply(lambda x: abs(float(x)) if pd.notna(x) else 0)
    df = df.sort_values("_abs", ascending=False).head(20)

    header = ["Date", "Merchant", "Category", "Amount", "Currency", "Source"]
    rows = [header]
    for _, r in df.iterrows():
        amt = r.get("amount")
        try:
            amt_f = float(amt)
            amt_str = f"${amt_f:,.2f}" if amt_f >= 0 else f"(${abs(amt_f):,.2f})"
        except (TypeError, ValueError):
            amt_str = "—"

        date_val = r.get("date")
        try:
            date_str = pd.Timestamp(date_val).strftime("%Y-%m-%d") if pd.notna(date_val) else "—"
        except Exception:
            date_str = str(date_val or "—")

        rows.append([
            date_str,
            str(r.get("merchant") or "—")[:28],
            str(r.get("category") or "—")[:18],
            amt_str,
            str(r.get("currency") or "CAD"),
            str(r.get("source") or "—").title(),
        ])

    col_w = [0.85*inch, 1.85*inch, 1.2*inch, 0.85*inch, 0.7*inch, 0.75*inch]
    t = Table(rows, colWidths=col_w, hAlign="LEFT")

    style = [
        ("BACKGROUND",    (0, 0), (-1, 0), _NAVY),
        ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 8),
        ("FONTNAME",      (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",      (0, 1), (-1, -1), 8),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, _LIGHT_ROW]),
        ("TEXTCOLOR",     (0, 1), (-1, -1), _TEXT),
        ("GRID",          (0, 0), (-1, -1), 0.3, _MID_GREY),
        ("BOX",           (0, 0), (-1, -1), 0.6, _NAVY),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("ALIGN",         (3, 0), (3, -1), "RIGHT"),
        ("ALIGN",         (4, 0), (4, -1), "CENTER"),
    ]

    # Colour negative amounts red, positive green (data rows only)
    for i, row in enumerate(rows[1:], start=1):
        amt_cell = row[3]
        if amt_cell.startswith("("):
            style.append(("TEXTCOLOR", (3, i), (3, i), _RED))
        elif amt_cell != "—":
            style.append(("TEXTCOLOR", (3, i), (3, i), _GREEN))

    t.setStyle(TableStyle(style))
    return t


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def generate_pdf_report(
    transactions: pd.DataFrame,
    analytics: AnalyticsSummary,
    receipts: pd.DataFrame | None = None,
    output_path: Path | None = None,
) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = output_path or REPORTS_DIR / f"financial_report_{datetime.now():%Y%m%d_%H%M%S}.pdf"

    doc = SimpleDocTemplate(
        str(path),
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )
    styles = _build_styles()
    story = []

    # ── Header ──────────────────────────────────────────────────────────────
    story.append(Paragraph("LedgerLens", styles["title"]))
    story.append(Paragraph(
        f"Financial Intelligence Report &nbsp;·&nbsp; Generated {datetime.now():%B %d, %Y at %H:%M}",
        styles["subtitle"],
    ))
    _divider(story)

    # ── KPI Summary ─────────────────────────────────────────────────────────
    story.append(Paragraph("Summary", styles["section"]))
    story.append(_summary_table(analytics))
    story.append(Spacer(1, 0.2 * inch))

    # ── Alerts ──────────────────────────────────────────────────────────────
    if analytics.flags:
        _divider(story)
        story.append(Paragraph("Alerts", styles["section"]))
        for flag in analytics.flags[:10]:
            level = (flag.get("level") or "").lower()
            s = styles["alert_high"] if level == "error" else styles["alert_low"]
            prefix = "✖" if level == "error" else "⚠"
            story.append(Paragraph(f"{prefix}  {flag['message']}", s))
        story.append(Spacer(1, 0.1 * inch))

    # ── Receipts ─────────────────────────────────────────────────────────────
    if receipts is not None and not receipts.empty:
        _divider(story)
        story.append(Paragraph(
            f"Receipts &nbsp;<font size='9' color='#6b7280'>({min(len(receipts), 30)} of {len(receipts)} shown)</font>",
            styles["section"],
        ))
        tbl = _receipt_table(receipts)
        if tbl:
            story.append(tbl)
        story.append(Spacer(1, 0.1 * inch))

    # ── Top Transactions ─────────────────────────────────────────────────────
    if not transactions.empty:
        _divider(story)
        story.append(Paragraph(
            "Top Transactions &nbsp;<font size='9' color='#6b7280'>(20 largest by value)</font>",
            styles["section"],
        ))
        tbl = _transaction_table(transactions)
        if tbl:
            story.append(tbl)
        story.append(Spacer(1, 0.08 * inch))
        story.append(Paragraph(
            f"Full transaction log contains {len(transactions):,} records across all sources.",
            styles["note"],
        ))

    doc.build(story)
    return path