"""One-off cleanup for invoices duplicated by the old vendor-based dedup key.

Groups existing invoices by (invoice_date, amount_incl, normalized invoice
number) and, for each group with more than one row, keeps a single survivor and
deletes the rest.

Survivor rule, in order:
  1. An invoice that has a match (deleting it would orphan reconciled work)
  2. Otherwise the oldest row by created_at (its Drive upload is the one
     already referenced elsewhere)

Groups where more than one row is matched are never touched — that needs a
human, so they are reported instead.

Usage:
    python scripts/dedupe_invoices.py            # dry run, prints the plan
    python scripts/dedupe_invoices.py --apply    # perform the deletions
"""

import asyncio
import sys
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.models.invoice import Invoice
from app.models.match import Match
from app.services.dedup import normalize_invoice_number


async def collect_groups(db: AsyncSession) -> list[list[Invoice]]:
    invoices = (await db.execute(select(Invoice))).scalars().all()

    groups: dict[tuple, list[Invoice]] = defaultdict(list)
    for inv in invoices:
        key = (
            inv.invoice_date,
            inv.amount_incl,
            normalize_invoice_number(inv.invoice_number),
        )
        groups[key].append(inv)

    return [g for g in groups.values() if len(g) > 1]


async def matched_invoice_ids(db: AsyncSession) -> set:
    rows = (await db.execute(select(Match.invoice_id))).scalars().all()
    return set(rows)


async def main(apply: bool) -> None:
    engine = create_async_engine(settings.database_url)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with Session() as db:
        groups = await collect_groups(db)
        has_match = await matched_invoice_ids(db)

        to_delete: list[Invoice] = []
        conflicts: list[list[Invoice]] = []

        for group in groups:
            matched = [i for i in group if i.id in has_match]

            if len(matched) > 1:
                conflicts.append(group)
                continue

            if matched:
                survivor = matched[0]
            else:
                survivor = min(group, key=lambda i: i.created_at)

            losers = [i for i in group if i.id != survivor.id]
            to_delete.extend(losers)

            print(f"\n{survivor.invoice_date}  {survivor.amount_incl}  "
                  f"[{normalize_invoice_number(survivor.invoice_number)}]")
            print(f"  KEEP   {survivor.vendor!r} / {survivor.invoice_number!r} "
                  f"({survivor.status}, created {survivor.created_at:%Y-%m-%d})")
            for loser in losers:
                print(f"  DELETE {loser.vendor!r} / {loser.invoice_number!r} "
                      f"({loser.status}, created {loser.created_at:%Y-%m-%d})")

        for group in conflicts:
            print(f"\n!! CONFLICT — {len(group)} rows in this group are matched, "
                  f"skipping. Resolve by hand:")
            for inv in group:
                print(f"   {inv.id}  {inv.vendor!r} / {inv.invoice_number!r} "
                      f"{inv.invoice_date} {inv.amount_incl} ({inv.status})")

        print(f"\n{'=' * 60}")
        print(f"duplicate groups : {len(groups)}")
        print(f"rows to delete   : {len(to_delete)}")
        print(f"conflicts        : {len(conflicts)}")

        if not apply:
            print("\nDry run. Re-run with --apply to delete.")
            await engine.dispose()
            return

        for inv in to_delete:
            await db.delete(inv)
        await db.commit()
        print(f"\nDeleted {len(to_delete)} duplicate invoices.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main(apply="--apply" in sys.argv))
