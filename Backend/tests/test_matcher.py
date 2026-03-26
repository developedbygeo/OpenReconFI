"""Unit tests for the deterministic matching engine (no DB, no LLM)."""

import uuid
from datetime import date
from decimal import Decimal

import pytest

from app.services.matcher import (
    ConversionFeeDismissal,
    InvoiceCandidate,
    MatchCandidate,
    TransactionCandidate,
    detect_conversion_fees,
    deterministic_match,
)


def _inv(amount: str, vendor: str = "Vercel", currency: str = "EUR", iban: str | None = None) -> InvoiceCandidate:
    return InvoiceCandidate(
        id=uuid.uuid4(),
        vendor=vendor,
        amount_incl=Decimal(amount),
        currency=currency,
        iban=iban,
    )


def _tx(
    amount: str,
    counterparty: str = "VERCEL INC",
    iban: str | None = None,
    description: str = "Payment",
    original_amount: str | None = None,
    original_currency: str | None = None,
    tx_date: date | None = None,
) -> TransactionCandidate:
    return TransactionCandidate(
        id=uuid.uuid4(),
        amount=Decimal(amount),
        counterparty=counterparty,
        counterparty_iban=iban,
        description=description,
        original_amount=Decimal(original_amount) if original_amount else None,
        original_currency=original_currency,
        tx_date=tx_date,
    )


class TestDeterministicMatch:
    """Tests for deterministic_match() pure function."""

    def test_amount_plus_iban_match(self):
        """Amount + IBAN → confidence 1.00."""
        inv = _inv("49.00", iban="NL91ABNA0417164300")
        tx = _tx("-49.00", iban="NL91ABNA0417164300")

        matches = deterministic_match([inv], [tx], {})
        assert len(matches) == 1
        assert matches[0].invoice_id == inv.id
        assert matches[0].transaction_id == tx.id
        assert matches[0].confidence == Decimal("1.00")
        assert "IBAN" in matches[0].rationale

    def test_amount_plus_alias_match(self):
        """Amount + vendor alias → confidence 0.95."""
        inv = _inv("49.00", vendor="Vercel")
        tx = _tx("-49.00", counterparty="VERCEL INC", iban=None)

        matches = deterministic_match([inv], [tx], {"Vercel": ["VERCEL INC"]})
        assert len(matches) == 1
        assert matches[0].confidence == Decimal("0.95")
        assert "alias" in matches[0].rationale

    def test_amount_only_left_for_llm(self):
        """Amount-only match (no IBAN or alias) → left for LLM, not matched."""
        inv = _inv("49.00", vendor="Vercel")
        tx = _tx("-49.00", counterparty="Unknown Corp", description="wire transfer")

        matches = deterministic_match([inv], [tx], {})
        assert len(matches) == 0

    def test_multiple_amount_matches_one_strong(self):
        """Multiple amount matches but one has alias → pick the strong one."""
        inv = _inv("49.00", vendor="Vercel")
        tx1 = _tx("-49.00", counterparty="VERCEL INC", description="payment")
        tx2 = _tx("-49.00", counterparty="Company B", description="payment")

        matches = deterministic_match([inv], [tx1, tx2], {"Vercel": ["VERCEL INC"]})
        assert len(matches) == 1
        assert matches[0].transaction_id == tx1.id
        assert matches[0].confidence == Decimal("0.95")

    def test_foreign_currency_match(self):
        """Invoice in USD matches transaction's original_amount in USD."""
        inv = _inv("99.00", vendor="Cloudflare", currency="USD")
        tx = _tx("-85.00", counterparty="CLOUDFLARE INC",
                 original_amount="99.00", original_currency="USD")

        matches = deterministic_match([inv], [tx], {"Cloudflare": ["CLOUDFLARE INC"]})
        assert len(matches) == 1
        assert matches[0].invoice_id == inv.id

    def test_no_match_different_amounts(self):
        """Different amounts → no match."""
        inv = _inv("49.00")
        tx = _tx("-50.00")

        matches = deterministic_match([inv], [tx], {})
        assert len(matches) == 0

    def test_one_to_one_conflict_resolution(self):
        """Two invoices want same transaction → highest confidence wins."""
        inv1 = _inv("49.00", vendor="Vercel", iban="NL91ABNA0417164300")
        inv2 = _inv("49.00", vendor="Other")
        tx = _tx("-49.00", counterparty="VERCEL INC", iban="NL91ABNA0417164300")

        matches = deterministic_match([inv1, inv2], [tx], {})
        assert len(matches) == 1
        assert matches[0].invoice_id == inv1.id
        assert matches[0].confidence == Decimal("1.00")

    def test_vendor_name_substring_match(self):
        """Direct vendor name appears in counterparty → alias match without explicit alias."""
        inv = _inv("12.10", vendor="Hetzner")
        tx = _tx("-12.10", counterparty="Hetzner Online GmbH", description="server hosting")

        matches = deterministic_match([inv], [tx], {})
        assert len(matches) == 1
        assert matches[0].confidence == Decimal("0.95")

    def test_vendor_name_partial_no_deterministic(self):
        """Counterparty is similar but not an exact substring → left for LLM."""
        inv = _inv("15.12", vendor="Adobe Systems Software Ireland Ltd")
        tx = _tx("-15.12", counterparty="Adobe Systems Software", description="payment")

        # No alias configured — deterministic pass skips, LLM handles it
        matches = deterministic_match([inv], [tx], {})
        assert len(matches) == 0

    def test_iban_normalization(self):
        """IBAN matching ignores spaces and case."""
        inv = _inv("49.00", iban="nl91 abna 0417 1643 00")
        tx = _tx("-49.00", iban="NL91ABNA0417164300")

        matches = deterministic_match([inv], [tx], {})
        assert len(matches) == 1
        assert matches[0].confidence == Decimal("1.00")


class TestConversionFeeDetection:
    """Tests for detect_conversion_fees()."""

    def test_fee_near_foreign_match(self):
        """Small fee tx near a foreign-currency match → dismissed."""
        inv = _inv("99.00", vendor="Cloudflare", currency="USD")
        main_tx = _tx("-85.00", counterparty="CLOUDFLARE INC",
                       original_amount="99.00", original_currency="USD",
                       tx_date=date(2026, 3, 15))
        fee_tx = _tx("-1.50", counterparty="Bank", description="Currency conversion fee",
                      tx_date=date(2026, 3, 15))

        matched = [MatchCandidate(
            invoice_id=inv.id,
            transaction_id=main_tx.id,
            confidence=Decimal("0.95"),
            rationale="test",
        )]

        dismissals = detect_conversion_fees(
            matched, [inv], [main_tx, fee_tx], {fee_tx.id},
        )
        assert len(dismissals) == 1
        assert dismissals[0].transaction_id == fee_tx.id

    def test_no_fee_when_amount_too_large(self):
        """Transaction > €5 should not be dismissed as fee."""
        inv = _inv("99.00", vendor="Cloudflare", currency="USD")
        main_tx = _tx("-85.00", counterparty="CLOUDFLARE INC",
                       original_amount="99.00", original_currency="USD",
                       tx_date=date(2026, 3, 15))
        big_tx = _tx("-10.00", counterparty="Bank", description="conversion fee",
                      tx_date=date(2026, 3, 15))

        matched = [MatchCandidate(
            invoice_id=inv.id,
            transaction_id=main_tx.id,
            confidence=Decimal("0.95"),
            rationale="test",
        )]

        dismissals = detect_conversion_fees(
            matched, [inv], [main_tx, big_tx], {big_tx.id},
        )
        assert len(dismissals) == 0

    def test_no_fee_when_too_far_apart(self):
        """Fee tx more than 3 days away → not dismissed."""
        inv = _inv("99.00", vendor="Cloudflare", currency="USD")
        main_tx = _tx("-85.00", counterparty="CLOUDFLARE INC",
                       original_amount="99.00", original_currency="USD",
                       tx_date=date(2026, 3, 10))
        fee_tx = _tx("-1.50", counterparty="Bank", description="conversion fee",
                      tx_date=date(2026, 3, 20))

        matched = [MatchCandidate(
            invoice_id=inv.id,
            transaction_id=main_tx.id,
            confidence=Decimal("0.95"),
            rationale="test",
        )]

        dismissals = detect_conversion_fees(
            matched, [inv], [main_tx, fee_tx], {fee_tx.id},
        )
        assert len(dismissals) == 0

    def test_no_fee_without_keyword(self):
        """Small nearby tx without fee keywords → not dismissed."""
        inv = _inv("99.00", vendor="Cloudflare", currency="USD")
        main_tx = _tx("-85.00", counterparty="CLOUDFLARE INC",
                       original_amount="99.00", original_currency="USD",
                       tx_date=date(2026, 3, 15))
        small_tx = _tx("-1.50", counterparty="Coffee Shop", description="latte",
                        tx_date=date(2026, 3, 15))

        matched = [MatchCandidate(
            invoice_id=inv.id,
            transaction_id=main_tx.id,
            confidence=Decimal("0.95"),
            rationale="test",
        )]

        dismissals = detect_conversion_fees(
            matched, [inv], [main_tx, small_tx], {small_tx.id},
        )
        assert len(dismissals) == 0

    def test_eur_match_no_fee_detection(self):
        """EUR-only match → no conversion fee detection."""
        inv = _inv("49.00", vendor="Vercel", currency="EUR")
        tx = _tx("-49.00", counterparty="VERCEL INC", tx_date=date(2026, 3, 15))
        fee_tx = _tx("-1.50", counterparty="Bank", description="conversion fee",
                      tx_date=date(2026, 3, 15))

        matched = [MatchCandidate(
            invoice_id=inv.id,
            transaction_id=tx.id,
            confidence=Decimal("0.95"),
            rationale="test",
        )]

        dismissals = detect_conversion_fees(
            matched, [inv], [tx, fee_tx], {fee_tx.id},
        )
        assert len(dismissals) == 0
