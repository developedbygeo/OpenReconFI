import json
from collections.abc import AsyncGenerator
from datetime import date
from decimal import Decimal
from typing import Optional

import anthropic
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.chat_message import ChatMessage
from app.models.enums import ChatRole, InvoiceStatus
from app.models.invoice import Invoice
from app.models.transaction import Transaction
from app.services.embeddings import embed_text

SYSTEM_PROMPT = """You are OpenReconFi's financial assistant. You help agency owners understand their full financial picture — expenses, revenue, bank transactions, invoices, taxes, and reconciliation status.

You have access to the agency's financial data, including:
- Invoices (expenses): amounts, vendors, categories, periods, and statuses
- Bank transactions: inflows (revenue), outflows (expenses), counterparties, and matching status
- Aggregated summaries: spend by category/vendor, monthly trends, inflow/outflow breakdowns, and reconciliation status

Guidelines:
- Be concise and direct. Use exact figures from the data provided.
- When making specific claims about invoices or transactions, reference invoice numbers or transaction IDs.
- Format monetary values with € and two decimal places.
- If the data doesn't contain enough information to answer, say so clearly.
- You can suggest follow-up questions the user might find useful.
- Never fabricate data. Only reference what's in the provided context."""


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------


async def _retrieve_similar_invoices(
    db: AsyncSession, query_vec: list[float], limit: int = 20
) -> list[Invoice]:
    """Find invoices most similar to the query vector."""
    result = await db.execute(
        select(Invoice)
        .where(Invoice.embedding.isnot(None))
        .order_by(Invoice.embedding.cosine_distance(query_vec))
        .limit(limit)
    )
    return list(result.scalars().all())


async def _retrieve_similar_transactions(
    db: AsyncSession, query_vec: list[float], limit: int = 20
) -> list[Transaction]:
    """Find transactions most similar to the query vector."""
    result = await db.execute(
        select(Transaction)
        .where(Transaction.embedding.isnot(None))
        .order_by(Transaction.embedding.cosine_distance(query_vec))
        .limit(limit)
    )
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Aggregates (always included as grounding data)
# ---------------------------------------------------------------------------


async def _build_aggregates(db: AsyncSession) -> str:
    """Build SQL aggregate summaries for grounding."""
    today = date.today()
    # Current + prior 3 months
    mom_periods = [
        f"{today.year}-{today.month:02d}",
    ]
    for i in range(1, 4):
        m = today.month - i
        y = today.year
        if m <= 0:
            m += 12
            y -= 1
        mom_periods.append(f"{y}-{m:02d}")
    mom_periods.reverse()

    parts: list[str] = []

    # Spend by category (all time)
    cat_result = await db.execute(
        select(
            func.coalesce(Invoice.category, "Uncategorized").label("cat"),
            func.sum(Invoice.amount_excl),
            func.count(Invoice.id),
        )
        .group_by(text("cat"))
        .order_by(func.sum(Invoice.amount_excl).desc())
        .limit(10)
    )
    cat_rows = cat_result.all()
    if cat_rows:
        parts.append("## Spend by Category (all time)")
        parts.append("| Category | Total ex VAT | Invoices |")
        parts.append("|---|---|---|")
        for row in cat_rows:
            parts.append(f"| {row[0]} | €{row[1]:,.2f} | {row[2]} |")

    # Spend by vendor (all time, top 10)
    vendor_result = await db.execute(
        select(
            Invoice.vendor,
            func.sum(Invoice.amount_excl),
            func.count(Invoice.id),
        )
        .group_by(Invoice.vendor)
        .order_by(func.sum(Invoice.amount_excl).desc())
        .limit(10)
    )
    vendor_rows = vendor_result.all()
    if vendor_rows:
        parts.append("\n## Spend by Vendor (top 10)")
        parts.append("| Vendor | Total ex VAT | Invoices |")
        parts.append("|---|---|---|")
        for row in vendor_rows:
            parts.append(f"| {row[0]} | €{row[1]:,.2f} | {row[2]} |")

    # MoM invoice trend
    mom_result = await db.execute(
        select(
            Invoice.period,
            func.sum(Invoice.amount_excl),
            func.count(Invoice.id),
        )
        .where(Invoice.period.in_(mom_periods))
        .group_by(Invoice.period)
        .order_by(Invoice.period)
    )
    mom_rows = mom_result.all()
    if mom_rows:
        parts.append(f"\n## Invoice Monthly Trend ({mom_periods[0]} – {mom_periods[-1]})")
        parts.append("| Period | Total ex VAT | Invoices |")
        parts.append("|---|---|---|")
        for row in mom_rows:
            parts.append(f"| {row[0]} | €{row[1]:,.2f} | {row[2]} |")

    # ── Bank Transaction Aggregates ──

    # Inflows vs outflows (all time)
    inflow_result = await db.execute(
        select(
            func.sum(Transaction.amount).filter(Transaction.amount > 0),
            func.count(Transaction.id).filter(Transaction.amount > 0),
            func.sum(Transaction.amount).filter(Transaction.amount < 0),
            func.count(Transaction.id).filter(Transaction.amount < 0),
        )
    )
    flow_row = inflow_result.one()
    inflows, inflow_count, outflows, outflow_count = flow_row
    if inflows or outflows:
        parts.append("\n## Bank Account Summary (all time)")
        parts.append("| Direction | Total | Transactions |")
        parts.append("|---|---|---|")
        if inflows:
            parts.append(f"| Inflows (revenue) | €{inflows:,.2f} | {inflow_count} |")
        if outflows:
            parts.append(f"| Outflows (all debits) | €{outflows:,.2f} | {outflow_count} |")
        if inflows and outflows:
            parts.append(f"| **Net** | **€{(inflows + outflows):,.2f}** | {inflow_count + outflow_count} |")
        parts.append("")
        parts.append("*Note: Outflows include ALL debits (business expenses, taxes, personal draws, etc). See 'Bank Transactions by Category' below for the breakdown.*")

    # Monthly bank trend
    tx_mom_result = await db.execute(
        select(
            Transaction.period,
            func.sum(Transaction.amount).filter(Transaction.amount > 0).label("inflows"),
            func.sum(Transaction.amount).filter(Transaction.amount < 0).label("outflows"),
            func.count(Transaction.id),
        )
        .where(Transaction.period.in_(mom_periods))
        .group_by(Transaction.period)
        .order_by(Transaction.period)
    )
    tx_mom_rows = tx_mom_result.all()
    if tx_mom_rows:
        parts.append(f"\n## Bank Monthly Trend ({mom_periods[0]} – {mom_periods[-1]})")
        parts.append("| Period | Inflows | Outflows | Net | Txns |")
        parts.append("|---|---|---|---|---|")
        for row in tx_mom_rows:
            inf = row[1] or Decimal(0)
            out = row[2] or Decimal(0)
            parts.append(f"| {row[0]} | €{inf:,.2f} | €{out:,.2f} | €{(inf + out):,.2f} | {row[3]} |")

    # Outflows by category (expenses breakdown — these sum to the total outflows above)
    tx_out_cat_result = await db.execute(
        select(
            func.coalesce(Transaction.category, "Uncategorized").label("cat"),
            func.sum(Transaction.amount),
            func.count(Transaction.id),
        )
        .where(Transaction.amount < 0)
        .group_by(text("cat"))
        .order_by(func.sum(Transaction.amount))
        .limit(10)
    )
    tx_out_cat_rows = tx_out_cat_result.all()
    if tx_out_cat_rows:
        parts.append("\n## Outflows by Category (breakdown of total outflows — do NOT double-count)")
        parts.append("| Category | Amount | Transactions |")
        parts.append("|---|---|---|")
        for row in tx_out_cat_rows:
            parts.append(f"| {row[0]} | €{row[1]:,.2f} | {row[2]} |")

    # Inflows by source (revenue breakdown — these sum to the total inflows above)
    tx_in_cat_result = await db.execute(
        select(
            Transaction.counterparty,
            func.sum(Transaction.amount),
            func.count(Transaction.id),
        )
        .where(Transaction.amount > 0)
        .group_by(Transaction.counterparty)
        .order_by(func.sum(Transaction.amount).desc())
        .limit(10)
    )
    tx_in_cat_rows = tx_in_cat_result.all()
    if tx_in_cat_rows:
        parts.append("\n## Revenue by Source (breakdown of total inflows — do NOT double-count)")
        parts.append("| Source | Amount | Transactions |")
        parts.append("|---|---|---|")
        for row in tx_in_cat_rows:
            parts.append(f"| {row[0]} | €{row[1]:,.2f} | {row[2]} |")

    # Top counterparties by volume
    cp_result = await db.execute(
        select(
            Transaction.counterparty,
            func.sum(Transaction.amount),
            func.count(Transaction.id),
        )
        .group_by(Transaction.counterparty)
        .order_by(func.abs(func.sum(Transaction.amount)).desc())
        .limit(10)
    )
    cp_rows = cp_result.all()
    if cp_rows:
        parts.append("\n## Top Counterparties by Volume (top 10)")
        parts.append("| Counterparty | Net Amount | Transactions |")
        parts.append("|---|---|---|")
        for row in cp_rows:
            parts.append(f"| {row[0]} | €{row[1]:,.2f} | {row[2]} |")

    # Transaction status breakdown
    status_result = await db.execute(
        select(
            Transaction.status,
            func.count(Transaction.id),
            func.sum(func.abs(Transaction.amount)),
        )
        .group_by(Transaction.status)
    )
    status_rows = status_result.all()
    if status_rows:
        parts.append("\n## Transaction Status Breakdown")
        parts.append("| Status | Count | Total Amount |")
        parts.append("|---|---|---|")
        for row in status_rows:
            parts.append(f"| {row[0].value} | {row[1]} | €{row[2]:,.2f} |")

    return "\n".join(parts) if parts else "No financial data available yet."



def _format_retrieved_invoices(invoices: list[Invoice]) -> str:
    """Format retrieved invoices as a compact markdown table."""
    if not invoices:
        return ""
    lines = ["## Retrieved Invoices"]
    lines.append("| ID | Vendor | Amount incl | Date | Period | Category | Status |")
    lines.append("|---|---|---|---|---|---|---|")
    for inv in invoices:
        lines.append(
            f"| {inv.id} | {inv.vendor} | €{inv.amount_incl:,.2f} | "
            f"{inv.invoice_date} | {inv.period} | {inv.category or '-'} | {inv.status.value} |"
        )
    return "\n".join(lines)


def _format_retrieved_transactions(txs: list[Transaction]) -> str:
    """Format retrieved transactions as a compact markdown table."""
    if not txs:
        return ""
    lines = ["\n## Retrieved Transactions"]
    lines.append("| ID | Counterparty | Description | Amount | Date | Status |")
    lines.append("|---|---|---|---|---|---|")
    for tx in txs:
        lines.append(
            f"| {tx.id} | {tx.counterparty} | {tx.description} | "
            f"€{tx.amount:,.2f} | {tx.tx_date} | {tx.status.value} |"
        )
    return "\n".join(lines)



def _get_client() -> anthropic.AsyncAnthropic:
    return anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)


async def chat_stream(
    db: AsyncSession,
    message: str,
) -> AsyncGenerator[str, None]:
    """Full RAG pipeline: embed query → retrieve → aggregate → stream Claude response.

    Yields text chunks as they arrive. After streaming, persists both user and
    assistant messages to chat_messages.
    """
    # 1. Embed the user query
    query_vec = await embed_text(message)

    # 2. Vector similarity search
    invoices = await _retrieve_similar_invoices(db, query_vec)
    transactions = await _retrieve_similar_transactions(db, query_vec)

    # 3. Build grounding aggregates
    aggregates = await _build_aggregates(db)

    # 4. Assemble context
    context_parts = [aggregates]
    inv_table = _format_retrieved_invoices(invoices)
    if inv_table:
        context_parts.append(inv_table)
    tx_table = _format_retrieved_transactions(transactions)
    if tx_table:
        context_parts.append(tx_table)
    context = "\n\n".join(context_parts)

    # 5. Load conversation history
    history_result = await db.execute(
        select(ChatMessage)
        .order_by(ChatMessage.created_at)
        .limit(50)
    )
    history = history_result.scalars().all()

    messages: list[dict] = []
    for msg in history:
        messages.append({"role": msg.role.value, "content": msg.content})

    # Add current user message with context
    user_turn = f"{message}\n\n---\n\n{context}"
    messages.append({"role": "user", "content": user_turn})

    # 6. Save user message
    invoice_ids = [inv.id for inv in invoices] if invoices else None
    tx_ids = [tx.id for tx in transactions] if transactions else None

    user_msg = ChatMessage(
        role=ChatRole.user,
        content=message,
        retrieved_invoice_ids=invoice_ids,
        retrieved_tx_ids=tx_ids,
    )
    db.add(user_msg)
    await db.commit()

    # 7. Stream Claude response
    client = _get_client()
    full_response: list[str] = []

    try:
        async with client.messages.stream(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=messages,
        ) as stream:
            async for text_chunk in stream.text_stream:
                full_response.append(text_chunk)
                yield text_chunk
    except anthropic.APIStatusError as e:
        error_msg = "Sorry, the AI service is temporarily unavailable. Please try again in a moment."
        if not full_response:
            yield error_msg
            full_response.append(error_msg)
        else:
            tail = "\n\n*[Response interrupted — service temporarily unavailable. Please try again.]*"
            yield tail
            full_response.append(tail)

    # 8. Save assistant message
    assistant_msg = ChatMessage(
        role=ChatRole.assistant,
        content="".join(full_response),
        retrieved_invoice_ids=invoice_ids,
        retrieved_tx_ids=tx_ids,
    )
    db.add(assistant_msg)
    await db.commit()


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------


async def get_chat_history(
    db: AsyncSession, limit: int = 100
) -> list[ChatMessage]:
    """Get chat history ordered by creation time."""
    result = await db.execute(
        select(ChatMessage)
        .order_by(ChatMessage.created_at)
        .limit(limit)
    )
    return list(result.scalars().all())


FALLBACK_STARTERS = [
    "What are my top vendors by spend?",
    "Show me this month's expenses vs last month.",
    "Are there any unmatched transactions?",
]

FALLBACK_FOLLOWUPS = [
    "Can you break that down by category?",
    "What about the previous month?",
    "Which invoices are still unpaid?",
]


async def generate_suggestions(db: AsyncSession) -> list[str]:
    """Generate 3 contextual chat suggestions using aggregates + Haiku."""
    aggregates = await _build_aggregates(db)

    # Load last 4 messages for conversation context
    history_result = await db.execute(
        select(ChatMessage)
        .order_by(ChatMessage.created_at.desc())
        .limit(4)
    )
    recent = list(reversed(history_result.scalars().all()))

    has_conversation = len(recent) > 0

    if has_conversation:
        conv_lines = [f"{m.role.value}: {m.content[:200]}" for m in recent]
        conv_context = "\n".join(conv_lines)
        prompt = (
            f"Financial data:\n{aggregates}\n\n"
            f"Recent conversation:\n{conv_context}\n\n"
            "Suggest 3 short follow-up questions (max 10 words each) the user might ask next "
            "about their finances. Return ONLY a JSON array of 3 strings, no other text."
        )
        fallback = FALLBACK_FOLLOWUPS
    else:
        prompt = (
            f"Financial data:\n{aggregates}\n\n"
            "Suggest 3 short starter questions (max 10 words each) a user might ask "
            "about these finances. Return ONLY a JSON array of 3 strings, no other text."
        )
        fallback = FALLBACK_STARTERS

    try:
        client = _get_client()
        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        questions = json.loads(text)
        if isinstance(questions, list) and len(questions) >= 3:
            return [str(q) for q in questions[:3]]
        return fallback
    except Exception:
        return fallback


async def clear_chat_history(db: AsyncSession) -> int:
    """Delete all chat messages. Returns count deleted."""
    result = await db.execute(select(func.count(ChatMessage.id)))
    count = result.scalar_one()
    await db.execute(text("DELETE FROM chat_messages"))
    await db.commit()
    return count
