"""One-shot script: embed all existing invoices and transactions that have embedding IS NULL."""

import asyncio

from app.db import AsyncSessionLocal
from app.services.embeddings import backfill_embeddings


async def main() -> None:
    async with AsyncSessionLocal() as db:
        result = await backfill_embeddings(db)
        print(f"Backfill complete: {result}")


if __name__ == "__main__":
    asyncio.run(main())
