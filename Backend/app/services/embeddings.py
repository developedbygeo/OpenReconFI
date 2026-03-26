from typing import Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.invoice import Invoice
from app.models.transaction import Transaction

OPENAI_EMBEDDINGS_URL = "https://api.openai.com/v1/embeddings"

def format_invoice_text(invoice: Invoice) -> str:
    """Format invoice fields into a short, structured string for embedding."""
    return (
        f"{invoice.vendor} {invoice.category or 'Uncategorized'} "
        f"{invoice.amount_incl}EUR {invoice.invoice_date} {invoice.period}"
    )


def format_transaction_text(tx: Transaction) -> str:
    """Format transaction fields into a short, structured string for embedding."""
    return (
        f"{tx.counterparty} {tx.description} "
        f"{tx.amount}EUR {tx.tx_date}"
    )

async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Call OpenAI embedding API and return vectors.

    Returns a list of embedding vectors, one per input text.
    Uses text-embedding-3-small with dimensions=1024 to match pgvector column.
    """
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            OPENAI_EMBEDDINGS_URL,
            headers={
                "Authorization": f"Bearer {settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "input": texts,
                "model": settings.embedding_model,
                "dimensions": settings.embedding_dim,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return [item["embedding"] for item in data["data"]]


async def embed_text(text: str) -> list[float]:
    """Embed a single text string."""
    results = await embed_texts([text])
    return results[0]

async def embed_invoice(db: AsyncSession, invoice: Invoice) -> None:
    """Embed an invoice and store the vector."""
    text = format_invoice_text(invoice)
    embedding = await embed_text(text)
    invoice.embedding = embedding
    await db.commit()


async def embed_transaction(db: AsyncSession, tx: Transaction) -> None:
    """Embed a transaction and store the vector."""
    text = format_transaction_text(tx)
    embedding = await embed_text(text)
    tx.embedding = embedding
    await db.commit()

async def backfill_embeddings(db: AsyncSession, batch_size: int = 50) -> dict:
    """Embed all invoices and transactions that have embedding IS NULL.

    Returns a summary dict with counts.
    """
    invoice_count = 0
    tx_count = 0

    # Backfill invoices
    while True:
        result = await db.execute(
            select(Invoice)
            .where(Invoice.embedding.is_(None))
            .limit(batch_size)
        )
        invoices = result.scalars().all()
        if not invoices:
            break

        texts = [format_invoice_text(inv) for inv in invoices]
        embeddings = await embed_texts(texts)
        for inv, emb in zip(invoices, embeddings):
            inv.embedding = emb
        await db.commit()
        invoice_count += len(invoices)

    # Backfill transactions
    while True:
        result = await db.execute(
            select(Transaction)
            .where(Transaction.embedding.is_(None))
            .limit(batch_size)
        )
        txs = result.scalars().all()
        if not txs:
            break

        texts = [format_transaction_text(tx) for tx in txs]
        embeddings = await embed_texts(texts)
        for tx, emb in zip(txs, embeddings):
            tx.embedding = emb
        await db.commit()
        tx_count += len(txs)

    return {"invoices_embedded": invoice_count, "transactions_embedded": tx_count}
