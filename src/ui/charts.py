"""Shared Plotly chart builders for the dashboard."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

PALETTE = {
    "primary": "#2563eb",
    "secondary": "#0ea5e9",
    "success": "#10b981",
    "warning": "#f59e0b",
    "danger": "#ef4444",
    "muted": "#94a3b8",
    "series": ["#2563eb", "#0ea5e9", "#10b981", "#8b5cf6", "#f59e0b", "#ef4444", "#64748b"],
}

CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, system-ui, sans-serif", color="#334155", size=13),
    margin=dict(l=24, r=24, t=48, b=24),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
)


def cash_flow_bar(monthly: pd.DataFrame) -> go.Figure:
    if monthly.empty:
        return _empty_figure("No monthly data yet")

    colors = [
        PALETTE["success"] if v >= 0 else PALETTE["danger"]
        for v in monthly["cash_flow"]
    ]
    fig = go.Figure(
        go.Bar(
            x=monthly["month"],
            y=monthly["cash_flow"],
            marker_color=colors,
            hovertemplate="%{x}<br>$%{y:,.2f}<extra></extra>",
        )
    )
    fig.update_layout(
        **CHART_LAYOUT,
        title="Monthly Cash Flow",
        xaxis_title="",
        yaxis_title="Amount ($)",
        yaxis=dict(gridcolor="#e2e8f0", zerolinecolor="#cbd5e1"),
    )
    return fig


def category_donut(by_category: pd.DataFrame) -> go.Figure:
    if by_category.empty:
        return _empty_figure("No category breakdown")

    df = by_category.copy()
    df["abs_total"] = df["total"].abs()
    fig = px.pie(
        df,
        names="category",
        values="abs_total",
        hole=0.55,
        color_discrete_sequence=PALETTE["series"],
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")
    fig.update_layout(**CHART_LAYOUT, title="Spend by Category", showlegend=False)
    return fig


def top_merchants_bar(top_merchants: pd.DataFrame) -> go.Figure:
    if top_merchants.empty:
        return _empty_figure("No merchant data")

    df = top_merchants.sort_values("spend")
    fig = go.Figure(
        go.Bar(
            x=df["spend"],
            y=df["merchant"],
            orientation="h",
            marker=dict(
                color=df["spend"],
                colorscale=[[0, "#dbeafe"], [1, PALETTE["primary"]]],
            ),
            hovertemplate="%{y}<br>$%{x:,.2f}<extra></extra>",
        )
    )
    fig.update_layout(
        **CHART_LAYOUT,
        title="Top Merchants by Spend",
        xaxis_title="Spend ($)",
        yaxis_title="",
        height=max(280, 40 * len(df)),
    )
    return fig


def payment_methods_chart(payment_methods: pd.DataFrame) -> go.Figure:
    if payment_methods.empty:
        return _empty_figure("No payment method data from receipts")

    fig = px.bar(
        payment_methods,
        x="method",
        y="count",
        color="method",
        color_discrete_sequence=PALETTE["series"],
    )
    fig.update_layout(**CHART_LAYOUT, title="Receipt Payment Methods", showlegend=False)
    return fig


def revenue_expense_gauge(revenue: float, expenses: float) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Indicator(
            mode="number+delta",
            value=revenue - expenses,
            title={"text": "Net Position"},
            delta={"reference": 0, "relative": False, "valueformat": ",.2f"},
            number={"prefix": "$", "valueformat": ",.2f"},
        )
    )
    fig.update_layout(**CHART_LAYOUT, height=180)
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
    fig.update_layout(**CHART_LAYOUT, height=320)
    return fig
