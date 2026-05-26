"""LedgerLens — financial insights dashboard."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from src.config import SHOEBOX_DIR
from src.ingestion.uploads import append_notes, save_invoices, save_receipts, save_statement
from src.pipeline import run_pipeline
from src.ui.charts import (
    cash_flow_bar,
    category_donut,
    payment_methods_chart,
    top_merchants_bar,
)
from src.ui.theme import CUSTOM_CSS, alert_html

st.set_page_config(
    page_title="LedgerLens",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


@st.cache_data(show_spinner=False, ttl=300)
def load_data(shoebox: str):
    return run_pipeline(Path(shoebox), generate_report=True)


def _fmt_money(val: float) -> str:
    sign = "+" if val >= 0 else ""
    return f"{sign}${val:,.2f}"


def _render_upload_panel(shoebox_path: Path):
    st.markdown("### Add documents")
    st.caption("Upload receipts (any rotation), statements, invoices, or notes.")

    with st.expander("Receipt images", expanded=False):
        receipt_files = st.file_uploader(
            "Photos / scans (JPG, PNG, WEBP…)",
            type=["jpg", "jpeg", "png", "webp", "gif", "bmp"],
            accept_multiple_files=True,
            key="upload_receipts",
        )
        if st.button("Save receipts", key="btn_receipts", width="stretch") and receipt_files:
            names = save_receipts(shoebox_path, receipt_files)
            st.success(f"Saved {len(names)} receipt(s)")
            st.cache_data.clear()
            st.rerun()

    with st.expander("Card statement (PDF)", expanded=False):
        stmt_file = st.file_uploader("PDF statement", type=["pdf"], key="upload_statement")
        if st.button("Save statement", key="btn_statement", width="stretch") and stmt_file:
            name = save_statement(shoebox_path, stmt_file)
            st.success(f"Saved {name}")
            st.cache_data.clear()
            st.rerun()

    with st.expander("Invoices (Excel)", expanded=False):
        inv_file = st.file_uploader("Excel workbook", type=["xlsx", "xls"], key="upload_invoices")
        if st.button("Save invoices", key="btn_invoices", width="stretch") and inv_file:
            name = save_invoices(shoebox_path, inv_file)
            st.success(f"Saved {name}")
            st.cache_data.clear()
            st.rerun()

    with st.expander("Notes", expanded=False):
        note_text = st.text_area(
            "Paste notes (expenses, todos, mentions)",
            height=120,
            placeholder="e.g. Petco charge was $47 — personal, move to personal card",
            key="upload_notes_text",
        )
        note_file = st.file_uploader("Or upload .txt / .md", type=["txt", "md"], key="upload_notes_file")
        if st.button("Save notes", key="btn_notes", width="stretch"):
            if note_text.strip() or note_file:
                name = append_notes(shoebox_path, note_text, note_file)
                st.success(f"Notes updated ({name})")
                st.cache_data.clear()
                st.rerun()
            else:
                st.warning("Add text or a file first.")


def _render_hero(analytics):
    period = "All periods"
    if analytics and not analytics.monthly.empty:
        months = analytics.monthly["month"].tolist()
        period = f"{months[0]} → {months[-1]}" if len(months) > 1 else months[0]

    st.markdown(
        f"""
        <div class="hero">
            <h1>LedgerLens</h1>
            <p>Revenue, spend, and receipt-backed insights · {period}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_kpis(analytics, tx_count: int):
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Revenue", f"${analytics.revenue:,.2f}", help="Invoices & inflows")
    k2.metric("Expenses", f"${analytics.expenses:,.2f}", help="Statements & card spend")
    k3.metric(
        "Net Cash Flow",
        _fmt_money(analytics.cash_flow),
        delta_color="normal" if analytics.cash_flow >= 0 else "inverse",
        help="Revenue minus expenses",
    )
    k4.metric(
        "Receipt spend",
        f"${analytics.receipt_total_spend:,.2f}",
        help=f"{analytics.receipt_count} receipt(s) extracted via Gemini",
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("Transactions", tx_count)
    c2.metric("Receipts scanned", analytics.receipt_count)
    c3.metric("Open alerts", len(analytics.flags))


def _render_receipt_gallery(receipts: pd.DataFrame, shoebox: Path):
    if receipts.empty:
        st.info("No receipts yet — upload images in the sidebar.")
        return

    receipts_dir = shoebox / "receipts"
    cols = st.columns(min(3, len(receipts)))
    for i, (_, row) in enumerate(receipts.iterrows()):
        with cols[i % len(cols)]:
            img_path = receipts_dir / str(row.get("source_file", ""))
            if img_path.is_file():
                st.image(str(img_path), width="stretch")

            merchant = row.get("merchant_raw") or "Unknown merchant"
            amt = row.get("amount")
            curr = row.get("currency") or "CAD"
            amt_s = f"${float(amt):,.2f}" if amt is not None and pd.notna(amt) else "—"
            pay = row.get("payment_method") or "—"
            date = row.get("date_raw") or "—"
            conf = row.get("confidence") or ""
            is_error = str(row.get("ocr_mode", "")).lower() == "error"

            badge = ""
            if is_error:
                badge = '<span class="match-badge" style="background:#fee2e2;color:#991b1b">Failed</span>'
            elif conf == "low" or merchant == "Unknown merchant" or amt_s == "—":
                badge = '<span class="match-badge" style="background:#fef3c7;color:#92400e">Low confidence</span>'
            else:
                badge = '<span class="match-badge">Parsed</span>'

            st.markdown(
                f"""
                <div class="receipt-card">
                    <div class="merchant">{merchant}{badge}</div>
                    <div class="meta">{date} · {amt_s} {curr} · {pay}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            line_items = row.get("line_items")
            if isinstance(line_items, list) and line_items:
                with st.expander("Line items"):
                    st.json(line_items)
            elif isinstance(line_items, str) and line_items.startswith("["):
                try:
                    st.json(json.loads(line_items))
                except json.JSONDecodeError:
                    pass

            notes = row.get("notes")
            if notes and not str(notes).startswith("ERROR"):
                st.caption(str(notes)[:200])


def _transactions_table(transactions: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "date",
        "merchant",
        "amount",
        "currency",
        "category",
        "source",
    ]
    available = [c for c in cols if c in transactions.columns]
    df = transactions[available].copy()
    if "date" in df.columns:
        df["date"] = df["date"].apply(
            lambda d: pd.Timestamp(d).strftime("%Y-%m-%d") if pd.notna(d) else ""
        )
    if "amount" in df.columns:
        df["amount"] = df["amount"].apply(
            lambda a: f"${float(a):,.2f}" if a is not None and pd.notna(a) else ""
        )
    return df


def main():
    shoebox_path = Path(st.session_state.get("shoebox", str(SHOEBOX_DIR)))

    with st.sidebar:
        st.markdown("### LedgerLens")
        shoebox = st.text_input("Data folder", value=str(shoebox_path))
        st.session_state["shoebox"] = shoebox
        shoebox_path = Path(shoebox)

        refresh = st.button("Refresh analysis", width="stretch", type="primary")
        if refresh:
            st.cache_data.clear()
            st.rerun()

        st.divider()
        _render_upload_panel(shoebox_path)

        st.divider()
        st.caption("Receipts use Gemini vision (handles rotation & handwriting).")

    if not shoebox_path.exists():
        st.error("Data folder not found.")
        shoebox_path.mkdir(parents=True, exist_ok=True)
        (shoebox_path / "receipts").mkdir(exist_ok=True)
        st.info("Created an empty shoebox — upload documents in the sidebar.")
        return

    rc = len(list((shoebox_path / "receipts").glob("*"))) if (shoebox_path / "receipts").exists() else 0
    pdfs = list(shoebox_path.glob("*.pdf"))
    st.caption(
        f"Shoebox: {rc} receipt file(s) · {len(pdfs)} statement PDF(s) · "
        f"{len(list(shoebox_path.glob('*.xlsx')))} invoice workbook(s)"
    )

    with st.spinner("Analyzing documents…"):
        try:
            result = load_data(str(shoebox_path))
        except EnvironmentError as e:
            st.error(str(e))
            st.info("Set `GEMINI_API_KEY` in `.env` for receipt extraction.")
            return
        except Exception as e:
            st.error(f"Analysis failed: {e}")
            st.exception(e)
            return

    analytics = result.analytics
    if not analytics:
        st.warning("No analytics available.")
        return

    _render_hero(analytics)
    _render_kpis(analytics, len(result.transactions))

    left, right = st.columns([1.4, 1])
    with left:
        st.plotly_chart(cash_flow_bar(analytics.monthly), width="stretch")
    with right:
        st.plotly_chart(category_donut(analytics.by_category), width="stretch")

    mid_l, mid_r = st.columns(2)
    with mid_l:
        st.plotly_chart(top_merchants_bar(analytics.top_merchants), width="stretch")
    with mid_r:
        st.plotly_chart(payment_methods_chart(analytics.payment_methods), width="stretch")

    st.markdown('<div class="section-title">Receipt gallery</div>', unsafe_allow_html=True)
    receipts = result.parsed.get("receipts", pd.DataFrame())
    _render_receipt_gallery(receipts, shoebox_path)

    st.markdown('<div class="section-title">All transactions</div>', unsafe_allow_html=True)
    st.dataframe(
        _transactions_table(result.transactions),
        width="stretch",
        hide_index=True,
        height=400,
    )

    if analytics.flags:
        st.markdown('<div class="section-title">Alerts</div>', unsafe_allow_html=True)
        for flag in analytics.flags:
            st.markdown(
                alert_html(flag.get("level", "info"), flag.get("message", "")),
                unsafe_allow_html=True,
            )

    if result.report_path and result.report_path.exists():
        st.divider()
        _, col_b = st.columns([3, 1])
        with col_b:
            with open(result.report_path, "rb") as f:
                st.download_button(
                    "Download PDF report",
                    f,
                    file_name=result.report_path.name,
                    mime="application/pdf",
                    width="stretch",
                )


if __name__ == "__main__":
    main()
