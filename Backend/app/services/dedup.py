"""Invoice deduplication.

The same invoice gets re-extracted whenever the extraction prompt changes, and
the LLM does not reproduce the vendor name or the invoice number byte-for-byte
between runs. Three drift modes have been observed in production:

  1. Vendor string      "Adobe Systems Software Ireland Ltd" → "Adobe"
  2. Separator drift    "U5YB9SXN 0001" → "U5YB9SXN-0001"
  3. Greek homoglyphs   "070Ρ-805091" → "070P-805091"  (Greek rho vs Latin P)

So the dedup key must not contain the vendor, and the invoice number has to be
normalized before comparison.
"""

from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invoice import Invoice

# Greek → Latin. Where a Greek letter has a Latin lookalike we map to the
# lookalike, because that is what the LLM produces when it reads the glyph off
# the PDF (Ρ → P, not R). The rest fall back to standard transliteration, which
# is what it produces when it transliterates instead (Δ → D).
GREEK_TO_LATIN = str.maketrans({
    # Visual homoglyphs
    "Α": "A", "Β": "B", "Ε": "E", "Ζ": "Z", "Η": "H", "Ι": "I", "Κ": "K",
    "Μ": "M", "Ν": "N", "Ο": "O", "Ρ": "P", "Τ": "T", "Υ": "Y", "Χ": "X",
    "α": "A", "β": "B", "ε": "E", "ζ": "Z", "η": "H", "ι": "I", "κ": "K",
    "μ": "M", "ν": "N", "ο": "O", "ρ": "P", "τ": "T", "υ": "Y", "χ": "X",
    # No Latin lookalike — transliterate
    "Γ": "G", "Δ": "D", "Θ": "TH", "Λ": "L", "Ξ": "X", "Π": "P", "Σ": "S",
    "Φ": "F", "Ψ": "PS", "Ω": "O", "ς": "S",
    "γ": "G", "δ": "D", "θ": "TH", "λ": "L", "ξ": "X", "π": "P", "σ": "S",
    "φ": "F", "ψ": "PS", "ω": "O",
})


def normalize_invoice_number(invoice_number: str) -> str:
    """Reduce an invoice number to a form stable across extraction runs.

    Uppercases, transliterates Greek to Latin, then drops everything that is
    not alphanumeric — separators are the least stable part of the string.

        "ΤΔΑ-Α-09490"   → "TDAA09490"
        "TDA-A-09490"   → "TDAA09490"
        "U5YB9SXN 0001" → "U5YB9SXN0001"
        "U5YB9SXN-0001" → "U5YB9SXN0001"
    """
    upper = invoice_number.upper().translate(GREEK_TO_LATIN)
    return "".join(ch for ch in upper if ch.isalnum())


async def find_duplicate_invoice(
    db: AsyncSession,
    invoice_number: str,
    invoice_date: Any,
    amount_incl: Decimal,
    exclude_id: Optional[UUID] = None,
) -> Optional[Invoice]:
    """Return an existing invoice that is the same document, or None.

    Two invoices are the same document when they share a date, an amount, and a
    normalized invoice number. Vendor is deliberately excluded — it is the field
    most likely to have been reworded by a newer extraction prompt.

    Date and amount are filtered in SQL; the number is normalized in Python
    because it is not stored normalized. The candidate set for a given
    (date, amount) is tiny, so this stays cheap.
    """
    target = normalize_invoice_number(invoice_number)
    if not target:
        return None

    query = select(Invoice).where(
        Invoice.invoice_date == invoice_date,
        Invoice.amount_incl == amount_incl,
    )
    if exclude_id is not None:
        query = query.where(Invoice.id != exclude_id)

    result = await db.execute(query)
    for candidate in result.scalars().all():
        if normalize_invoice_number(candidate.invoice_number) == target:
            return candidate

    return None
