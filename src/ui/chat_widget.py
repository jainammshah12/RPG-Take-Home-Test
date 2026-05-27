"""Fixed bottom-right chat widget for the LedgerLens dashboard."""

from __future__ import annotations

import streamlit as st

from src.ui.chat_assistant import build_dashboard_context, generate_reply
from src.ui.theme import CHAT_CSS

_WELCOME = (
    "Hi! I'm **LedgerLens Assistant**. Ask me about your revenue, card spend, "
    "invoices, receipts, or anything on the dashboard."
)

_SUGGESTIONS = [
    "What's my net cash flow?",
    "Who are my top clients?",
    "Summarize my card spend",
    "Any outstanding invoices?",
]


def _init_chat_state():
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = [{"role": "assistant", "content": _WELCOME}]
    if "chat_context_key" not in st.session_state:
        st.session_state.chat_context_key = None
    if "chat_open" not in st.session_state:
        st.session_state.chat_open = False


def _reset_chat():
    st.session_state.chat_messages = [{"role": "assistant", "content": _WELCOME}]
    st.session_state.chat_context_key = None


def _context_fingerprint(result) -> str:
    a = result.analytics
    if not a:
        return "empty"
    return f"{a.revenue:.0f}-{a.expenses:.0f}-{len(result.transactions)}"


def _render_chat_messages():
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])


def _handle_user_message(prompt: str, context: str):
    st.session_state.chat_messages.append({"role": "user", "content": prompt})
    reply = generate_reply(prompt, context, st.session_state.chat_messages[:-1])
    st.session_state.chat_messages.append({"role": "assistant", "content": reply})


def render_floating_chat(result):
    """Render a fixed bottom-right chat dock (FAB + slide-up panel)."""
    _init_chat_state()
    st.markdown(CHAT_CSS, unsafe_allow_html=True)

    context = build_dashboard_context(result)
    st.session_state["_chat_context"] = context

    fp = _context_fingerprint(result)
    if st.session_state.chat_context_key != fp:
        st.session_state.chat_context_key = fp
        if len(st.session_state.chat_messages) > 1:
            st.session_state.chat_messages.append(
                {
                    "role": "assistant",
                    "content": "_Dashboard data was refreshed - my answers now reflect the latest numbers._",
                }
            )

    if st.session_state.chat_open:
        with st.container(key="chat_panel"):
            head_l, head_r = st.columns([4, 1])
            head_l.markdown("##### LedgerLens Assistant")
            head_r.caption("Gemini")
            if st.button("Close", key="chat_close", width="stretch"):
                st.session_state.chat_open = False
                st.rerun()

            st.caption("Answers use your live dashboard data")

            clear_col, _ = st.columns([1, 3])
            with clear_col:
                if st.button("Clear chat", key="chat_clear", width="stretch"):
                    _reset_chat()
                    st.rerun()

            with st.container(height=300):
                _render_chat_messages()

            s1, s2 = st.columns(2)
            for i, suggestion in enumerate(_SUGGESTIONS):
                col = s1 if i % 2 == 0 else s2
                with col:
                    if st.button(suggestion, key=f"chat_suggest_{i}", width="stretch"):
                        with st.spinner("Thinking..."):
                            _handle_user_message(suggestion, context)
                        st.rerun()

            if prompt := st.chat_input("Ask about your finances...", key="ledgerlens_chat_input"):
                with st.spinner("Thinking..."):
                    _handle_user_message(prompt, context)
                st.rerun()

    with st.container(key="chat_fab"):
        label = "Close chat" if st.session_state.chat_open else "Ask LedgerLens"
        icon = "✕" if st.session_state.chat_open else "💬"
        if st.button(f"{icon} {label}", key="chat_toggle", width="stretch"):
            st.session_state.chat_open = not st.session_state.chat_open
            st.rerun()
