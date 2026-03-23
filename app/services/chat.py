"""Chat service — RAG pipeline for expense chat."""

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

SYSTEM_PROMPT = """You are Matchbook's financial assistant. You help agency owners understand their expenses, invoices, and transactions.

You have access to the agency's financial data, including invoices, bank transactions, vendor information, and spending summaries.

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

    # MoM trend
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
        parts.append(f"\n## Monthly Trend ({mom_periods[0]} – {mom_periods[-1]})")
        parts.append("| Period | Total ex VAT | Invoices |")
        parts.append("|---|---|---|")
        for row in mom_rows:
            parts.append(f"| {row[0]} | €{row[1]:,.2f} | {row[2]} |")

    return "\n".join(parts) if parts else "No financial data available yet."


# ---------------------------------------------------------------------------
# Context builder
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Chat (streaming)
# ---------------------------------------------------------------------------


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

    async with client.messages.stream(
        model="claude-sonnet-4-20250514",
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=messages,
    ) as stream:
        async for text_chunk in stream.text_stream:
            full_response.append(text_chunk)
            yield text_chunk

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


async def clear_chat_history(db: AsyncSession) -> int:
    """Delete all chat messages. Returns count deleted."""
    result = await db.execute(select(func.count(ChatMessage.id)))
    count = result.scalar_one()
    await db.execute(text("DELETE FROM chat_messages"))
    await db.commit()
    return count
