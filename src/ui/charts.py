"""Plotly charts using high-coverage fields only."""

import pandas as pd
import plotly.graph_objects as go

PALETTE = {
    "primary": "#2563eb",
    "secondary": "#0ea5e9",
    "success": "#10b981",
    "warning": "#f59e0b",
    "danger": "#ef4444",
    "muted": "#94a3b8",
    "series": ["#2563eb", "#0ea5e9", "#10b981", "#8b5cf6", "#f59e0b", "#ef4444", "#64748b"],
    "source": {
        "statement": "#2563eb",
        "invoice": "#10b981",
        "receipt": "#8b5cf6",
        "note": "#f59e0b",
    },
}

_BASE_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, system-ui, sans-serif", color="#334155", size=13),
    margin=dict(l=24, r=24, t=48, b=24),
)


def _layout(**overrides) -> dict:
    """Merge base layout with per-chart overrides (avoids duplicate kwargs)."""
    return {**_BASE_LAYOUT, **overrides}


def cash_flow_bar(monthly: pd.DataFrame) -> go.Figure:
    if monthly.empty:
        return _empty_figure("No dated transactions for monthly view")

    colors = [PALETTE["success"] if v >= 0 else PALETTE["danger"] for v in monthly["cash_flow"]]
    fig = go.Figure(
        go.Bar(
            x=monthly["month"],
            y=monthly["cash_flow"],
            marker_color=colors,
            hovertemplate="%{x}<br>$%{y:,.2f}<extra></extra>",
        )
    )
    fig.update_layout(
        **_layout(
            title="Monthly Net Cash Flow",
            yaxis_title="Amount ($)",
            yaxis=dict(gridcolor="#e2e8f0", zerolinecolor="#cbd5e1"),
            showlegend=False,
        )
    )
    return fig


def card_spend_bar(monthly_card_spend: pd.DataFrame) -> go.Figure:
    if monthly_card_spend.empty:
        return _empty_figure("No statement dates for card spend trend")

    fig = go.Figure(
        go.Bar(
            x=monthly_card_spend["month"],
            y=monthly_card_spend["card_spend"],
            marker_color=PALETTE["primary"],
            hovertemplate="%{x}<br>$%{y:,.2f}<extra></extra>",
        )
    )
    fig.update_layout(
        **_layout(
            title="Monthly Card Spend (Statement)",
            yaxis_title="Spend ($)",
            yaxis=dict(gridcolor="#e2e8f0"),
            showlegend=False,
        )
    )
    return fig


def by_source_chart(by_source: pd.DataFrame) -> go.Figure:
    if by_source.empty:
        return _empty_figure("No source breakdown")

    labels = [s.title() for s in by_source["source"]]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            name="Inflow",
            x=labels,
            y=by_source["inflow"],
            marker_color=PALETTE["success"],
            hovertemplate="%{x}<br>In: $%{y:,.2f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            name="Outflow",
            x=labels,
            y=by_source["outflow"],
            marker_color=PALETTE["danger"],
            hovertemplate="%{x}<br>Out: $%{y:,.2f}<extra></extra>",
        )
    )
    fig.update_layout(
        **_layout(
            title="Inflows vs Outflows by Source",
            barmode="group",
            yaxis_title="Amount ($)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        )
    )
    return fig


def top_merchants_bar(top_merchants: pd.DataFrame) -> go.Figure:
    if top_merchants.empty:
        return _empty_figure("No merchant spend data")

    df = top_merchants.sort_values("spend")
    fig = go.Figure(
        go.Bar(
            x=df["spend"],
            y=df["merchant"],
            orientation="h",
            marker_color=PALETTE["primary"],
            hovertemplate="%{y}<br>$%{x:,.2f}<extra></extra>",
        )
    )
    fig.update_layout(
        **_layout(
            title="Top Merchants (Card Statement)",
            xaxis_title="Spend ($)",
            height=max(280, 36 * len(df)),
            showlegend=False,
        )
    )
    return fig


def invoice_status_chart(invoice_status: pd.DataFrame) -> go.Figure:
    if invoice_status.empty:
        return _empty_figure("No invoice data")

    colors = [
        PALETTE["success"] if s.lower() == "paid" else PALETTE["warning"]
        for s in invoice_status["status"]
    ]
    fig = go.Figure(
        go.Bar(
            x=invoice_status["status"],
            y=invoice_status["amount"],
            marker_color=colors,
            text=invoice_status["count"].apply(lambda n: f"{n} inv."),
            textposition="outside",
            hovertemplate="%{x}<br>$%{y:,.2f}<br>%{text}<extra></extra>",
        )
    )
    fig.update_layout(
        **_layout(
            title="Invoices by Status",
            yaxis_title="Amount ($)",
            showlegend=False,
        )
    )
    return fig


def revenue_clients_bar(top_revenue_clients: pd.DataFrame) -> go.Figure:
    if top_revenue_clients.empty:
        return _empty_figure("No client revenue data")

    df = top_revenue_clients.sort_values("revenue")
    fig = go.Figure(
        go.Bar(
            x=df["revenue"],
            y=df["client"],
            orientation="h",
            marker_color=PALETTE["success"],
            hovertemplate="%{y}<br>$%{x:,.2f}<extra></extra>",
        )
    )
    fig.update_layout(
        **_layout(
            title="Revenue by Client (Invoices)",
            xaxis_title="Amount ($)",
            height=max(260, 32 * len(df)),
            showlegend=False,
        )
    )
    return fig


def _empty_figure(message: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(size=14, color=PALETTE["muted"]),
    )
    fig.update_layout(**_layout(height=320, showlegend=False))
    return fig
