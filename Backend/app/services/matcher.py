import logging
import re
from calendar import monthrange
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from difflib import SequenceMatcher
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ConfirmedBy, InvoiceStatus, TransactionStatus
from app.models.invoice import Invoice
from app.models.match import Match
from app.models.transaction import Transaction
from app.models.vendor import Vendor
from app.services.dedup import GREEK_TO_LATIN

logger = logging.getLogger(__name__)

FEE_KEYWORDS = {"conversion", "fee", "kosten", "wisselkoers", "commission", "currency"}
FEE_MAX_AMOUNT = Decimal("5.00")
FEE_DATE_TOLERANCE_DAYS = 3

# Settlement lag (tx_date - invoice_date), from the distribution of confirmed
# matches: median +3, 95% inside [-3, +12], outliers to -28 (end-of-month
# invoicing for a charge earlier in the month). The gate is set just outside the
# observed range — wide enough for real lag, tight enough that a monthly
# subscription cannot reach the neighbouring month's charge.
MIN_LAG_DAYS = -31
MAX_LAG_DAYS = 21

# Date proximity ranks candidates rather than gating them: a 3-day lag costs
# 0.015 confidence, a 30-day lag the full 0.15.
DATE_PENALTY_PER_DAY = Decimal("0.005")
MAX_DATE_PENALTY = Decimal("0.15")

# A pair is only emitted if it beats the runner-up on both sides by this much.
# Anything closer is genuinely ambiguous and goes to the LLM.
AMBIGUITY_MARGIN = Decimal("0.02")

# Vendor signal strength, before the date penalty.
IBAN_SCORE = Decimal("1.00")
NAME_SCORE = Decimal("0.95")
TOKEN_SCORE = Decimal("0.92")
FUZZY_SCORE = Decimal("0.90")

FUZZY_THRESHOLD = 0.85
MIN_TOKEN_LEN = 4

# A foreign-currency invoice settled in EUR, where the bank did not report the
# original amount (only 12 of 196 transactions carry it). The amount cannot be
# compared directly, so the pair is accepted on vendor + date + a plausible
# implied rate. Observed USD→EUR rates sit between 0.856 and 0.910 including
# card FX markup; the band is deliberately wider to cover other currencies.
FX_MIN_IMPLIED_RATE = Decimal("0.75")
FX_MAX_IMPLIED_RATE = Decimal("1.35")

# Ranks below every exact-amount tier, so an exact match always wins.
FX_SCORE = Decimal("0.88")


@dataclass
class InvoiceCandidate:
    id: UUID
    vendor: str
    amount_incl: Decimal
    currency: Optional[str] = None
    iban: Optional[str] = None
    invoice_date: Optional[date] = None


@dataclass
class TransactionCandidate:
    id: UUID
    amount: Decimal
    original_amount: Optional[Decimal] = None
    original_currency: Optional[str] = None
    counterparty: str = ""
    counterparty_iban: Optional[str] = None
    description: str = ""
    tx_date: Optional[date] = None


@dataclass
class MatchCandidate:
    invoice_id: UUID
    transaction_id: UUID
    confidence: Decimal
    rationale: str


@dataclass
class ConversionFeeDismissal:
    transaction_id: UUID
    near_match_invoice_id: UUID
    note: str


@dataclass
class MatchingResult:
    deterministic_matches: list[MatchCandidate] = field(default_factory=list)
    llm_matches: list[dict[str, Any]] = field(default_factory=list)
    fees_dismissed: list[ConversionFeeDismissal] = field(default_factory=list)


def _amounts_match(inv: InvoiceCandidate, tx: TransactionCandidate) -> bool:
    """Check if invoice and transaction amounts match (EUR or foreign currency)."""
    tx_abs = abs(tx.amount)

    # Direct EUR match
    if inv.amount_incl == tx_abs:
        return True

    # Foreign currency: invoice amount matches original_amount in same currency
    if (
        tx.original_amount is not None
        and tx.original_currency is not None
        and inv.currency is not None
        and inv.currency == tx.original_currency
        and inv.amount_incl == abs(tx.original_amount)
    ):
        return True

    return False


def _plausible_fx_conversion(inv: InvoiceCandidate, tx: TransactionCandidate) -> bool:
    """Could this EUR charge be this foreign-currency invoice, converted?

    Only for invoices not already in EUR, and only when the bank gave us no
    original amount to compare against — otherwise `_amounts_match` decides.
    """
    if inv.currency is None or inv.currency == "EUR":
        return False
    if tx.original_amount is not None:
        return False

    tx_abs = abs(tx.amount)
    if inv.amount_incl <= 0 or tx_abs <= 0:
        return False

    implied_rate = tx_abs / inv.amount_incl
    return FX_MIN_IMPLIED_RATE <= implied_rate <= FX_MAX_IMPLIED_RATE


def _iban_match(inv: InvoiceCandidate, tx: TransactionCandidate) -> bool:
    """Check if both have non-null IBANs that match exactly."""
    return (
        inv.iban is not None
        and tx.counterparty_iban is not None
        and inv.iban.replace(" ", "").upper() == tx.counterparty_iban.replace(" ", "").upper()
    )


# Legal-form suffixes carry no identifying information and are exactly what
# differs between an invoice header ("Adobe Systems Software Ireland Ltd") and a
# bank counterparty ("Adobe Systems Software"). Written in source form and
# folded below, so the Greek entries do not have to be hand-transliterated.
_RAW_LEGAL_SUFFIXES = (
    "inc incorporated ltd limited llc lp plc pbc bv nv gmbh ag sa sas srl spa "
    "ab oy as aps pty corp corporation co company holding holdings group "
    "international ireland emea europe eu usa "
    "ΑΕ ΕΠΕ ΙΚΕ ΟΕ ΕΕ ΜΟΝΟΠΡΟΣΩΠΗ ΙΔΙΩΤΙΚΗ ΚΕΦΑΛΑΙΟΥΧΙΚΗ ΕΤΑΙΡΕΙΑ ΑΝΩΝΥΜΗ"
).split()

# Words that appear in bank descriptions rather than in company names.
_NOISE_TOKENS = {
    "payment", "invoice", "transfer", "sepa", "ideal", "card", "subscr",
    "subscription", "purchase", "the", "and", "for", "com", "www", "http",
    "https", "net", "org",
}


def _fold(text: str) -> str:
    """Lowercase, transliterate Greek to Latin, reduce punctuation to spaces."""
    latin = text.translate(GREEK_TO_LATIN).lower()
    return "".join(ch if ch.isalnum() else " " for ch in latin)


_LEGAL_SUFFIXES = {_fold(s).strip() for s in _RAW_LEGAL_SUFFIXES}


def _name_tokens(text: str) -> list[str]:
    """Fold a company or counterparty name into identifying tokens."""
    return [
        t for t in _fold(text).split()
        if t and t not in _LEGAL_SUFFIXES and t not in _NOISE_TOKENS
    ]


def _normalize_name(text: str) -> str:
    """Fold a name to a comparable string with legal form and noise removed."""
    return " ".join(_name_tokens(text))


def normalized_alias(text: str) -> str:
    """Public form of the name normalizer, for storing learned vendor aliases."""
    return _normalize_name(text)


def _names_refer_to_same_party(a: str, b: str) -> Optional[Decimal]:
    """Score how strongly two names refer to the same party, or None.

    Deliberately symmetric. The old one-directional `vendor in counterparty`
    test failed whenever the invoice carried the longer name — "Autohellas
    Hertz" is not a substring of "Autohellas", so an exact amount match on a
    genuine pair scored nothing.
    """
    na, nb = _normalize_name(a), _normalize_name(b)
    if not na or not nb:
        return None

    if na == nb:
        return NAME_SCORE

    # Containment either way: "adobe" vs "adobe systems software".
    if len(na) >= MIN_TOKEN_LEN and len(nb) >= MIN_TOKEN_LEN:
        if na in nb or nb in na:
            return NAME_SCORE

    # A shared distinctive token: "autohellas hertz" vs "autohellas".
    ta, tb = set(_name_tokens(a)), set(_name_tokens(b))
    shared = {t for t in ta & tb if len(t) >= MIN_TOKEN_LEN}
    if shared:
        return TOKEN_SCORE

    # Spelling drift, mostly from transliteration: "skroytz" vs "skroutz".
    if SequenceMatcher(None, na, nb).ratio() >= FUZZY_THRESHOLD:
        return FUZZY_SCORE

    return None


def _vendor_signal(
    inv: InvoiceCandidate,
    tx: TransactionCandidate,
    vendor_aliases: dict[str, list[str]],
) -> Optional[tuple[Decimal, str]]:
    """Best vendor-name score for this pair, with a rationale, or None.

    Compares the invoice vendor against the counterparty, the description, and
    the aliases of every vendor record whose own name refers to the same party.
    That last part matters: aliases used to be applied only when the vendor
    record's name matched the invoice string exactly, so aliases learned as
    "Adobe Systems Software Ireland Ltd" were invisible to an invoice that now
    says "Adobe".
    """
    best: Optional[tuple[Decimal, str]] = None

    def offer(score: Optional[Decimal], rationale: str) -> None:
        nonlocal best
        if score is not None and (best is None or score > best[0]):
            best = (score, rationale)

    offer(_names_refer_to_same_party(inv.vendor, tx.counterparty), "vendor name")

    # The description is free text, so only accept a token hit inside it.
    desc_tokens = set(_name_tokens(tx.description))
    vendor_tokens = {t for t in _name_tokens(inv.vendor) if len(t) >= MIN_TOKEN_LEN}
    if vendor_tokens & desc_tokens:
        offer(TOKEN_SCORE, "vendor name in description")

    for vendor_name, aliases in vendor_aliases.items():
        if _names_refer_to_same_party(inv.vendor, vendor_name) is None:
            continue
        for alias in aliases:
            offer(_names_refer_to_same_party(alias, tx.counterparty), "vendor alias")
            alias_tokens = {t for t in _name_tokens(alias) if len(t) >= MIN_TOKEN_LEN}
            if alias_tokens & desc_tokens:
                offer(TOKEN_SCORE, "vendor alias in description")

    return best


def _date_penalty(inv: InvoiceCandidate, tx: TransactionCandidate) -> Optional[Decimal]:
    """Confidence penalty for the settlement lag, or None if out of range.

    Returns zero when either date is missing — an absent date is not evidence
    against a pair, it just cannot contribute one way or the other.
    """
    if inv.invoice_date is None or tx.tx_date is None:
        return Decimal("0")

    lag = (tx.tx_date - inv.invoice_date).days
    if lag < MIN_LAG_DAYS or lag > MAX_LAG_DAYS:
        return None

    return min(MAX_DATE_PENALTY, abs(lag) * DATE_PENALTY_PER_DAY)


def deterministic_match(
    invoices: list[InvoiceCandidate],
    transactions: list[TransactionCandidate],
    vendor_aliases: dict[str, list[str]],
) -> list[MatchCandidate]:
    """
    Pure deterministic matching: amount + date window + IBAN/vendor identity.

    A pair must clear three gates — the amount, a settlement lag inside
    [MIN_LAG_DAYS, MAX_LAG_DAYS], and either a matching IBAN or a vendor name
    that refers to the same party. It is then scored, with distant dates
    penalised so the nearest plausible transaction wins.

    Confidence tiers, before the date penalty:
    - 1.00: exact amount + IBAN match
    - 0.95: exact amount + vendor names match (equal, or one contains the other)
    - 0.92: exact amount + vendor names share a distinctive token
    - 0.90: exact amount + vendor names are a close spelling variant
    - 0.88: foreign-currency invoice, plausible converted amount + vendor name

    A pair is only emitted when it is the clear best for its invoice *and* for
    its transaction, by at least AMBIGUITY_MARGIN. Genuine ties — two identical
    subscription charges a fortnight apart — go to the LLM rather than being
    guessed at. Amount-only matches, with no IBAN or vendor signal, also go to
    the LLM.

    Returns matches after 1:1 conflict resolution (greedy by confidence desc).
    """
    # Score every pair that clears the gates.
    scored: list[MatchCandidate] = []

    for inv in invoices:
        for tx in transactions:
            exact_amount = _amounts_match(inv, tx)
            if not exact_amount and not _plausible_fx_conversion(inv, tx):
                continue

            penalty = _date_penalty(inv, tx)
            if penalty is None:
                continue

            signal = _vendor_signal(inv, tx, vendor_aliases)

            if not exact_amount:
                # Converted amount: the vendor name is carrying the whole claim,
                # so a mere spelling-similarity guess is not enough.
                if signal is None or signal[0] < TOKEN_SCORE:
                    continue
                base = FX_SCORE
                rationale = (
                    f"{signal[1]} match + amount consistent with "
                    f"{inv.currency}→EUR conversion"
                )
            elif _iban_match(inv, tx):
                base, rationale = IBAN_SCORE, "Amount + IBAN match"
            elif signal is not None:
                base, rationale = signal[0], f"Amount + {signal[1]} match"
            else:
                continue

            scored.append(MatchCandidate(
                invoice_id=inv.id,
                transaction_id=tx.id,
                confidence=base - penalty,
                rationale=rationale,
            ))

    # Drop pairs that are not a clear winner on both sides. Checking the
    # transaction side too catches two invoices competing for one charge, which
    # the invoice-side check alone would let through.
    by_invoice: dict[UUID, list[Decimal]] = {}
    by_transaction: dict[UUID, list[Decimal]] = {}
    for c in scored:
        by_invoice.setdefault(c.invoice_id, []).append(c.confidence)
        by_transaction.setdefault(c.transaction_id, []).append(c.confidence)

    def is_clear_winner(scores: list[Decimal], score: Decimal) -> bool:
        rivals = sorted(scores, reverse=True)
        if len(rivals) == 1:
            return True
        return score == rivals[0] and score - rivals[1] >= AMBIGUITY_MARGIN

    unambiguous = [
        c for c in scored
        if is_clear_winner(by_invoice[c.invoice_id], c.confidence)
        and is_clear_winner(by_transaction[c.transaction_id], c.confidence)
    ]

    # 1:1 conflict resolution: sort by confidence desc, greedy assignment
    unambiguous.sort(key=lambda c: c.confidence, reverse=True)
    used_invoices: set[UUID] = set()
    used_transactions: set[UUID] = set()
    resolved: list[MatchCandidate] = []

    for c in unambiguous:
        if c.invoice_id in used_invoices or c.transaction_id in used_transactions:
            continue
        used_invoices.add(c.invoice_id)
        used_transactions.add(c.transaction_id)
        resolved.append(c)

    return resolved


def detect_conversion_fees(
    matched_foreign: list[MatchCandidate],
    invoices: list[InvoiceCandidate],
    transactions: list[TransactionCandidate],
    remaining_tx_ids: set[UUID],
) -> list[ConversionFeeDismissal]:
    """
    For each foreign-currency match, find nearby small fee transactions to auto-dismiss.
    """
    # Build lookup for matched invoices that involved foreign currency
    foreign_match_info: list[tuple[UUID, date, UUID]] = []
    inv_map = {i.id: i for i in invoices}
    tx_map = {t.id: t for t in transactions}

    for mc in matched_foreign:
        inv = inv_map.get(mc.invoice_id)
        tx = tx_map.get(mc.transaction_id)
        if inv and tx and inv.currency and inv.currency != "EUR" and tx.tx_date:
            foreign_match_info.append((mc.invoice_id, tx.tx_date, tx.id))

    if not foreign_match_info:
        return []

    dismissals: list[ConversionFeeDismissal] = []
    dismissed_ids: set[UUID] = set()

    for inv_id, match_date, _match_tx_id in foreign_match_info:
        for tx in transactions:
            if tx.id not in remaining_tx_ids or tx.id in dismissed_ids:
                continue
            if tx.tx_date is None:
                continue

            # Check proximity
            delta = abs((tx.tx_date - match_date).days)
            if delta > FEE_DATE_TOLERANCE_DAYS:
                continue

            # Check small amount
            if abs(tx.amount) > FEE_MAX_AMOUNT:
                continue

            # Check fee keywords (whole word match to avoid false positives like "coffee")
            desc_lower = tx.description.lower() + " " + tx.counterparty.lower()
            if any(re.search(rf"\b{kw}\b", desc_lower) for kw in FEE_KEYWORDS):
                dismissals.append(ConversionFeeDismissal(
                    transaction_id=tx.id,
                    near_match_invoice_id=inv_id,
                    note=f"Currency conversion fee (auto-dismissed, near foreign-currency match)",
                ))
                dismissed_ids.add(tx.id)

    return dismissals


def _invoice_to_candidate(inv: Invoice) -> InvoiceCandidate:
    raw = inv.raw_extraction or {}
    return InvoiceCandidate(
        id=inv.id,
        vendor=inv.vendor,
        amount_incl=Decimal(str(inv.amount_incl)),
        currency=inv.currency,
        iban=raw.get("iban"),
        invoice_date=inv.invoice_date,
    )


def _transaction_to_candidate(tx: Transaction) -> TransactionCandidate:
    return TransactionCandidate(
        id=tx.id,
        amount=Decimal(str(tx.amount)),
        original_amount=Decimal(str(tx.original_amount)) if tx.original_amount else None,
        original_currency=tx.original_currency,
        counterparty=tx.counterparty or "",
        counterparty_iban=tx.counterparty_iban,
        description=tx.description or "",
        tx_date=tx.tx_date,
    )


async def run_matching(
    db: AsyncSession,
    period: Optional[str] = None,
) -> MatchingResult:
    """
    Two-pass hybrid matching orchestrator.

    1. Fetch all unmatched invoices + transactions (optionally filtered by period)
    2. Run deterministic pass → persist matches
    3. Detect + dismiss conversion fees
    4. Run LLM pass on leftovers → post-validate → persist
    5. Return breakdown
    """
    from app.services.llm import match_single_invoice

    result = MatchingResult()

    # --- Fetch unmatched invoices (include previous month for cross-period) ---
    inv_query = select(Invoice).where(
        Invoice.status.in_([InvoiceStatus.pending, InvoiceStatus.unmatched, InvoiceStatus.deferred])
    )
    if period:
        y, m = int(period[:4]), int(period[5:7])
        prev_m = m - 1 if m > 1 else 12
        prev_y = y if m > 1 else y - 1
        prev_period = f"{prev_y}-{prev_m:02d}"
        inv_query = inv_query.where(Invoice.period.in_([period, prev_period]))
    inv_result = await db.execute(inv_query)
    invoices = inv_result.scalars().all()

    # --- Fetch unmatched transactions (include boundary days) ---
    tx_query = select(Transaction).where(
        Transaction.status == TransactionStatus.unmatched
    )
    if period:
        y, m = int(period[:4]), int(period[5:7])
        prev_m = m - 1 if m > 1 else 12
        prev_y = y if m > 1 else y - 1
        prev_last_day = date(prev_y, prev_m, monthrange(prev_y, prev_m)[1])
        next_m = m + 1 if m < 12 else 1
        next_y = y if m < 12 else y + 1
        next_first_day = date(next_y, next_m, 1)
        tx_query = tx_query.where(
            or_(
                Transaction.period == period,
                Transaction.tx_date == prev_last_day,
                Transaction.tx_date == next_first_day,
            )
        )
    tx_result = await db.execute(tx_query)
    transactions = tx_result.scalars().all()

    if not invoices or not transactions:
        return result

    # --- Fetch vendor aliases ---
    vendor_result = await db.execute(select(Vendor))
    vendors = vendor_result.scalars().all()
    vendor_aliases: dict[str, list[str]] = {
        v.name: v.aliases or [] for v in vendors
    }

    # --- Convert to candidates ---
    inv_candidates = [_invoice_to_candidate(inv) for inv in invoices]
    tx_candidates = [_transaction_to_candidate(tx) for tx in transactions]

    # --- Pass 1: Deterministic matching ---
    logger.info("Matching: %d invoices, %d transactions", len(invoices), len(transactions))
    det_matches = deterministic_match(inv_candidates, tx_candidates, vendor_aliases)

    # Persist deterministic matches
    matched_inv_ids: set[UUID] = set()
    matched_tx_ids: set[UUID] = set()

    for mc in det_matches:
        match_obj = Match(
            invoice_id=mc.invoice_id,
            transaction_id=mc.transaction_id,
            confidence=mc.confidence,
            rationale=mc.rationale,
            confirmed_by=ConfirmedBy.deterministic,
        )
        db.add(match_obj)

        # Update statuses
        inv_obj = await db.get(Invoice, mc.invoice_id)
        if inv_obj:
            inv_obj.status = InvoiceStatus.matched
        tx_obj = await db.get(Transaction, mc.transaction_id)
        if tx_obj:
            tx_obj.status = TransactionStatus.matched
            if inv_obj and inv_obj.category and not tx_obj.category:
                tx_obj.category = inv_obj.category

        matched_inv_ids.add(mc.invoice_id)
        matched_tx_ids.add(mc.transaction_id)

    logger.info("Deterministic pass: %d matches", len(det_matches))
    result.deterministic_matches = det_matches

    # --- Conversion fee detection ---
    remaining_tx_ids = {tx.id for tx in transactions} - matched_tx_ids
    fee_dismissals = detect_conversion_fees(
        det_matches, inv_candidates, tx_candidates, remaining_tx_ids,
    )
    for fd in fee_dismissals:
        tx_obj = await db.get(Transaction, fd.transaction_id)
        if tx_obj:
            tx_obj.status = TransactionStatus.no_invoice
            tx_obj.note = fd.note
        remaining_tx_ids.discard(fd.transaction_id)

    result.fees_dismissed = fee_dismissals

    # --- Pass 2: LLM matching on leftovers ---
    leftover_invs = [inv for inv in invoices if inv.id not in matched_inv_ids]
    leftover_txs = [tx for tx in transactions if tx.id in remaining_tx_ids]

    logger.info("LLM pass: %d invoices, %d transactions remaining", len(leftover_invs), len(leftover_txs))
    if leftover_invs and leftover_txs:
        used_tx_ids: set[UUID] = set()

        for inv in leftover_invs:
            available_txs = [tx for tx in leftover_txs if tx.id not in used_tx_ids]
            if not available_txs:
                break

            inv_data = {
                "id": str(inv.id),
                "vendor": inv.vendor,
                "amount_incl": str(inv.amount_incl),
                "currency": inv.currency,
                "invoice_date": str(inv.invoice_date),
            }
            tx_data = [
                {
                    "id": str(tx.id),
                    "tx_date": str(tx.tx_date),
                    "amount": str(tx.amount),
                    "counterparty": tx.counterparty,
                    "description": tx.description,
                }
                for tx in available_txs
            ]

            try:
                s = await match_single_invoice(inv_data, tx_data)
            except Exception:
                logger.exception("LLM matching failed for %s", inv.vendor)
                continue

            if not s:
                logger.info("LLM: no match for %s", inv.vendor)
                continue

            tx_id = s["transaction_id"]
            logger.info("LLM match: %s → %s (conf=%s) — %s",
                        inv.vendor, tx_id, s["confidence"], s["rationale"])

            # Post-validate: amount sanity (reject >30% difference)
            tx_obj_check = next((tx for tx in available_txs if tx.id == tx_id), None)
            if tx_obj_check:
                inv_amt = Decimal(str(inv.amount_incl))
                tx_amt = abs(Decimal(str(tx_obj_check.amount)))
                if inv_amt > 0 and tx_amt > 0:
                    ratio = min(inv_amt, tx_amt) / max(inv_amt, tx_amt)
                    if ratio < Decimal("0.70"):
                        logger.info("Rejected: %s→%s (amount ratio %.2f)",
                                    inv.vendor, tx_obj_check.counterparty, ratio)
                        continue

            match_obj = Match(
                invoice_id=inv.id,
                transaction_id=tx_id,
                confidence=s["confidence"],
                rationale=s["rationale"],
                confirmed_by=ConfirmedBy.llm,
            )
            db.add(match_obj)

            inv.status = InvoiceStatus.matched
            tx_obj = await db.get(Transaction, tx_id)
            if tx_obj:
                tx_obj.status = TransactionStatus.matched
                if inv.category and not tx_obj.category:
                    tx_obj.category = inv.category

            used_tx_ids.add(tx_id)
            result.llm_matches.append(s)

    # --- Auto-categorize transactions that will never match an invoice ---
    # Withholdings → "Owner Draw"
    withholding_txs = await db.execute(
        select(Transaction).where(
            Transaction.status == TransactionStatus.withholding,
            Transaction.category.is_(None),
        )
    )
    for tx in withholding_txs.scalars().all():
        tx.category = "Owner Draw"

    # Unmatched inflows → "Revenue"
    revenue_txs = await db.execute(
        select(Transaction).where(
            Transaction.status == TransactionStatus.unmatched,
            Transaction.amount > 0,
            Transaction.category.is_(None),
        )
    )
    for tx in revenue_txs.scalars().all():
        tx.category = "Revenue"

    await db.commit()
    return result
