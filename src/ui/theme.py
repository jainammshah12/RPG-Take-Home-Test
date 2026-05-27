"""Dashboard styling injected into Streamlit."""

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', system-ui, sans-serif;
}

#MainMenu, footer, header[data-testid="stHeader"] {
    visibility: hidden;
}

.block-container {
    padding-top: 1.5rem;
    padding-bottom: 3rem;
    max-width: 1280px;
}

.hero {
    background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 55%, #2563eb 100%);
    border-radius: 16px;
    padding: 2rem 2.25rem;
    color: #f8fafc;
    margin-bottom: 1.5rem;
    box-shadow: 0 20px 40px rgba(15, 23, 42, 0.18);
}

.hero h1 {
    font-size: 1.85rem;
    font-weight: 700;
    margin: 0 0 0.35rem 0;
    letter-spacing: -0.02em;
}

.hero p {
    margin: 0;
    opacity: 0.85;
    font-size: 0.95rem;
}

.kpi-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1rem;
    margin-bottom: 1.5rem;
}

@media (max-width: 900px) {
    .kpi-grid { grid-template-columns: repeat(2, 1fr); }
}

.kpi-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    padding: 1.1rem 1.25rem;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
}

.kpi-label {
    font-size: 0.78rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #64748b;
    margin-bottom: 0.35rem;
}

.kpi-value {
    font-size: 1.65rem;
    font-weight: 700;
    color: #0f172a;
    line-height: 1.1;
}

.kpi-value.positive { color: #059669; }
.kpi-value.negative { color: #dc2626; }

.kpi-sub {
    font-size: 0.8rem;
    color: #94a3b8;
    margin-top: 0.25rem;
}

.section-title {
    font-size: 1.1rem;
    font-weight: 600;
    color: #0f172a;
    margin: 1.5rem 0 0.75rem 0;
}

.alert-card {
    border-radius: 10px;
    padding: 0.75rem 1rem;
    margin-bottom: 0.5rem;
    font-size: 0.9rem;
    border-left: 4px solid;
}

.alert-warning { background: #fffbeb; border-color: #f59e0b; color: #92400e; }
.alert-error   { background: #fef2f2; border-color: #ef4444; color: #991b1b; }
.alert-info    { background: #eff6ff; border-color: #3b82f6; color: #1e40af; }

.receipt-card {
    background: #fff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 1rem 1.1rem;
    margin-bottom: 0.75rem;
}

.receipt-card .merchant {
    font-weight: 600;
    color: #0f172a;
    font-size: 1rem;
}

.receipt-card .meta {
    color: #64748b;
    font-size: 0.82rem;
    margin-top: 0.25rem;
}

.match-badge {
    display: inline-block;
    background: #d1fae5;
    color: #065f46;
    font-size: 0.72rem;
    font-weight: 600;
    padding: 0.15rem 0.5rem;
    border-radius: 999px;
    margin-left: 0.5rem;
}

[data-testid="stSidebar"] {
    background: #f8fafc;
    border-right: 1px solid #e2e8f0;
}

/* Fixed bottom-right chat dock */
div.st-key-chat_fab {
    position: fixed !important;
    bottom: 1.25rem !important;
    right: 1.25rem !important;
    z-index: 10001 !important;
    width: auto !important;
    min-width: 3.25rem !important;
}

div.st-key-chat_fab button {
    background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 999px !important;
    font-weight: 600 !important;
    padding: 0.7rem 1.15rem !important;
    box-shadow: 0 4px 24px rgba(37, 99, 235, 0.5) !important;
    white-space: nowrap !important;
}

div.st-key-chat_fab button:hover {
    box-shadow: 0 8px 32px rgba(37, 99, 235, 0.6) !important;
}

div.st-key-chat_panel {
    position: fixed !important;
    bottom: 5.5rem !important;
    right: 1.25rem !important;
    z-index: 10000 !important;
    width: 22rem !important;
    max-width: calc(100vw - 2.5rem) !important;
    max-height: min(70vh, 520px) !important;
    overflow-y: auto !important;
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 16px !important;
    padding: 1rem 1.1rem 0.75rem !important;
    box-shadow: 0 16px 48px rgba(15, 23, 42, 0.2) !important;
}

@media (max-width: 768px) {
    div.st-key-chat_panel {
        width: calc(100vw - 2.5rem) !important;
        right: 1.25rem !important;
        left: 1.25rem !important;
        width: auto !important;
    }
}
</style>
"""

CHAT_CSS = """
<style>
section.main .block-container {
    padding-bottom: 6rem;
}
</style>
"""


def kpi_card(label: str, value: str, sub: str = "", tone: str = "") -> str:
    tone_class = f" kpi-value {tone}" if tone else " kpi-value"
    sub_html = f'<div class="kpi-sub">{sub}</div>' if sub else ""
    return f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="{tone_class.strip()}">{value}</div>
        {sub_html}
    </div>
    """


def alert_html(level: str, message: str) -> str:
    return f'<div class="alert-card alert-{level}">{message}</div>'
