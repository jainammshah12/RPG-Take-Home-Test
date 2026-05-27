"""Groq-powered dashboard assistant."""

from __future__ import annotations

import os
import time

from groq import Groq, RateLimitError

_MODEL = "llama-3.3-70b-versatile"

_SYSTEM_TEMPLATE = """You are LedgerLens Assistant - a friendly financial analyst chatbot embedded in a small-business dashboard.

You help users understand their revenue, card spend, invoices, and receipts. Answer clearly and concisely in plain language. Use bullet points for lists. Format dollar amounts like $1,234.56.

RULES:
- Only answer using the dashboard context below and the conversation. If data is missing, say so.
- Do not invent transactions, clients, or amounts not in the context.
- You are not a tax lawyer or accountant - add a brief disclaimer for tax/legal questions.
- Keep replies under 200 words unless the user asks for detail.

DASHBOARD CONTEXT:
{context}
"""


def build_dashboard_context(result) -> str:
    """Serialize pipeline results into a compact context block for the LLM."""
    lines: list[str] = []
    a = result.analytics
    if not a:
        return "No analytics loaded."

    lines.extend(
        [
            f"Revenue: ${a.revenue:,.2f}",
            f"Expenses: ${a.expenses:,.2f}",
            f"Net cash flow: ${a.cash_flow:,.2f}",
            f"Card statement lines: {a.statement_tx_count}",
            f"Receipts parsed: {a.receipt_count} (extracted spend ${a.receipt_total_spend:,.2f})",
            f"Invoices paid: ${a.invoice_paid_amount:,.2f}",
            f"Invoices pending: ${a.invoice_pending_amount:,.2f}",
        ]
    )

    if not a.by_source.empty:
        lines.append("\nBy data source:")
        for _, row in a.by_source.iterrows():
            lines.append(
                f"  - {row['source']}: {int(row['count'])} records, "
                f"in ${row['inflow']:,.2f}, out ${row['outflow']:,.2f}"
            )

    if not a.top_merchants.empty:
        lines.append("\nTop card merchants by spend:")
        for _, row in a.top_merchants.head(5).iterrows():
            lines.append(f"  - {row['merchant']}: ${row['spend']:,.2f}")

    if not a.top_revenue_clients.empty:
        lines.append("\nTop invoice clients:")
        for _, row in a.top_revenue_clients.head(5).iterrows():
            lines.append(f"  - {row['client']}: ${row['revenue']:,.2f}")

    if not a.invoice_status.empty:
        lines.append("\nInvoice status:")
        for _, row in a.invoice_status.iterrows():
            lines.append(f"  - {row['status']}: {int(row['count'])} invoices, ${row['amount']:,.2f}")

    if not a.spend_by_category.empty:
        lines.append("\nExpense categories:")
        for _, row in a.spend_by_category.iterrows():
            lines.append(f"  - {row['category']}: ${row['spend']:,.2f}")

    if a.flags:
        lines.append("\nAlerts:")
        for flag in a.flags[:8]:
            lines.append(f"  - [{flag.get('level')}] {flag.get('message')}")

    tx = result.transactions
    if tx is not None and not tx.empty:
        lines.append(f"\nTotal unified transactions: {len(tx)}")
        sample = tx.head(12)
        cols = [c for c in ("date", "merchant", "category", "amount", "source") if c in sample.columns]
        if cols:
            lines.append("Recent transactions (sample):")
            for _, row in sample.iterrows():
                date = row.get("date", "")
                if hasattr(date, "strftime"):
                    date = date.strftime("%Y-%m-%d")
                amt = row.get("amount", "")
                cat = row.get("category", "")
                cat_s = f" | {cat}" if cat and str(cat) != "nan" else ""
                lines.append(
                    f"  - {date} | {row.get('merchant', '')}{cat_s} | ${float(amt):,.2f} | {row.get('source', '')}"
                )

    receipts = result.parsed.get("receipts")
    if receipts is not None and not receipts.empty:
        lines.append("\nReceipt extractions:")
        for _, row in receipts.iterrows():
            m = row.get("merchant_raw") or "?"
            amt = row.get("amount")
            amt_s = f"${float(amt):,.2f}" if amt is not None and str(amt) != "nan" else "?"
            lines.append(f"  - {row.get('source_file')}: {m} - {amt_s}")

    return "\n".join(lines)


def _missing_key_message() -> str:
    return (
        "I need a **GROQ_API_KEY** in your `.env` file to answer questions. "
        "Get one at https://console.groq.com/keys"
    )


def _rate_limited_message() -> str:
    return (
        "I'm temporarily rate-limited by the Groq API. "
        "Please wait a minute and try again, or check your quota at "
        "https://console.groq.com"
    )


def _build_messages(user_message: str, context: str, history: list[dict]) -> list[dict]:
    system = _SYSTEM_TEMPLATE.format(context=context)
    messages: list[dict] = [{"role": "system", "content": system}]
    for msg in history[-10:]:
        role = msg.get("role", "user")
        if role not in ("user", "assistant"):
            continue
        text = msg.get("content", "")
        if text:
            messages.append({"role": role, "content": text})
    messages.append({"role": "user", "content": user_message})
    return messages


def generate_reply(
    user_message: str,
    context: str,
    history: list[dict],
) -> str:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return _missing_key_message()

    client = Groq(api_key=api_key)
    messages = _build_messages(user_message, context, history)

    try:
        response = client.chat.completions.create(
            model=_MODEL,
            messages=messages,
            temperature=0.3,
            max_tokens=1024,
        )
        reply = (response.choices[0].message.content or "").strip()
        return reply or "I could not generate a response. Please try rephrasing your question."
    except RateLimitError:
        time.sleep(2)
        try:
            response = client.chat.completions.create(
                model=_MODEL,
                messages=messages,
                temperature=0.3,
                max_tokens=1024,
            )
            reply = (response.choices[0].message.content or "").strip()
            return reply or "I'm temporarily rate-limited. Please wait a minute and try again."
        except Exception:
            return _rate_limited_message()
    except Exception as exc:
        err = str(exc).lower()
        if "429" in err or "quota" in err or "rate" in err:
            return _rate_limited_message()
        if "api" in err and "key" in err:
            return _missing_key_message()
        return "I couldn't generate a reply right now. Please try again in a moment."
