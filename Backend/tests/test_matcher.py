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


def _inv(
    amount: str,
    vendor: str = "Vercel",
    currency: str = "EUR",
    iban: str | None = None,
    invoice_date: date | None = None,
) -> InvoiceCandidate:
    return InvoiceCandidate(
        id=uuid.uuid4(),
        vendor=vendor,
        amount_incl=Decimal(amount),
        currency=currency,
        iban=iban,
        invoice_date=invoice_date,
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

    def test_amount_plus_vendor_name_match(self):
        """Amount + vendor name → confidence 0.95. The legal suffix is ignored."""
        inv = _inv("49.00", vendor="Vercel")
        tx = _tx("-49.00", counterparty="VERCEL INC", iban=None)

        matches = deterministic_match([inv], [tx], {"Vercel": ["VERCEL INC"]})
        assert len(matches) == 1
        assert matches[0].confidence == Decimal("0.95")
        assert "vendor name" in matches[0].rationale

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

    def test_invoice_vendor_longer_than_counterparty(self):
        """Invoice carries the legal name, bank carries the short one → match."""
        inv = _inv("15.12", vendor="Adobe Systems Software Ireland Ltd")
        tx = _tx("-15.12", counterparty="Adobe Systems Software", description="payment")

        matches = deterministic_match([inv], [tx], {})
        assert len(matches) == 1
        assert matches[0].confidence == Decimal("0.95")

    def test_vendor_name_suffix_only_difference(self):
        """"Autohellas Hertz" vs "AUTOHELLAS" — the old substring test failed here."""
        inv = _inv("440.45", vendor="Autohellas Hertz")
        tx = _tx("-440.45", counterparty="AUTOHELLAS", description="car lease")

        matches = deterministic_match([inv], [tx], {})
        assert len(matches) == 1
        assert matches[0].confidence == Decimal("0.95")

    def test_shared_token_only(self):
        """Names overlap on one distinctive token but neither contains the other."""
        inv = _inv("50.00", vendor="Autohellas Hertz")
        tx = _tx("-50.00", counterparty="HERTZ RENTAL", description="car")

        matches = deterministic_match([inv], [tx], {})
        assert len(matches) == 1
        assert matches[0].confidence == Decimal("0.92")

    def test_unrelated_vendor_still_no_match(self):
        """Same amount, unrelated names → still left for the LLM."""
        inv = _inv("20.00", vendor="Vercel")
        tx = _tx("-20.00", counterparty="The Burger Room", description="lunch")

        assert deterministic_match([inv], [tx], {}) == []

    def test_nearest_date_wins_over_distant_one(self):
        """Two same-amount charges for one vendor → the one in the lag window wins."""
        inv = _inv("15.12", vendor="Adobe", invoice_date=date(2026, 5, 11))
        near = _tx("-15.12", counterparty="Adobe Systems Software",
                   tx_date=date(2026, 5, 14))
        far = _tx("-15.12", counterparty="Adobe Systems Software",
                  tx_date=date(2026, 7, 15))

        matches = deterministic_match([inv], [near, far], {})
        assert len(matches) == 1
        assert matches[0].transaction_id == near.id

    def test_out_of_window_transaction_not_matched(self):
        """Next month's identical subscription charge is out of reach."""
        inv = _inv("15.12", vendor="Adobe", invoice_date=date(2026, 4, 11))
        tx = _tx("-15.12", counterparty="Adobe Systems Software",
                 tx_date=date(2026, 6, 13))

        assert deterministic_match([inv], [tx], {}) == []

    def test_negative_lag_within_window(self):
        """End-of-month invoice for a charge earlier that month still matches."""
        inv = _inv("32.40", vendor="Google Cloud", invoice_date=date(2026, 4, 30))
        tx = _tx("-32.40", counterparty="Google Workspace", tx_date=date(2026, 4, 8))

        matches = deterministic_match([inv], [tx], {})
        assert len(matches) == 1

    def test_equidistant_duplicates_are_ambiguous(self):
        """Two equally plausible charges → no guess, hand to the LLM."""
        inv = _inv("11.25", vendor="Vercel", invoice_date=date(2026, 6, 10))
        tx1 = _tx("-11.25", counterparty="VERCEL INC", tx_date=date(2026, 6, 7))
        tx2 = _tx("-11.25", counterparty="VERCEL INC", tx_date=date(2026, 6, 13))

        assert deterministic_match([inv], [tx1, tx2], {}) == []

    def test_two_invoices_one_transaction_is_ambiguous(self):
        """Duplicate invoices competing for one charge → neither is guessed."""
        inv1 = _inv("70.00", vendor="Acme", invoice_date=date(2026, 5, 15))
        inv2 = _inv("70.00", vendor="Acme", invoice_date=date(2026, 5, 15))
        tx = _tx("-70.00", counterparty="ACME", tx_date=date(2026, 5, 18))

        assert deterministic_match([inv1, inv2], [tx], {}) == []

    def test_date_penalty_lowers_confidence(self):
        """A distant but unambiguous pair matches at reduced confidence."""
        inv = _inv("99.00", vendor="Hetzner", invoice_date=date(2026, 5, 1))
        tx = _tx("-99.00", counterparty="Hetzner Online", tx_date=date(2026, 5, 21))

        matches = deterministic_match([inv], [tx], {})
        assert len(matches) == 1
        assert matches[0].confidence == Decimal("0.95") - Decimal("0.100")

    def test_missing_dates_do_not_block_match(self):
        """Candidates without dates still match on amount + vendor."""
        inv = _inv("49.00", vendor="Vercel")
        tx = _tx("-49.00", counterparty="VERCEL INC")

        assert len(deterministic_match([inv], [tx], {})) == 1

    def test_alias_applies_across_vendor_name_variants(self):
        """Alias learned under the legal name still helps the short-name invoice."""
        inv = _inv("18.55", vendor="OpenAI", invoice_date=date(2026, 4, 2))
        tx = _tx("-18.55", counterparty="CHATGPT SUBSCR", tx_date=date(2026, 4, 3))

        matches = deterministic_match(
            [inv], [tx], {"OpenAI Ireland Limited": ["CHATGPT SUBSCR"]}
        )
        assert len(matches) == 1
        assert "alias" in matches[0].rationale

    def test_usd_invoice_matches_converted_eur_charge(self):
        """USD invoice, EUR charge, bank reported no original amount."""
        inv = _inv("20.00", vendor="Resend", currency="USD",
                   invoice_date=date(2026, 6, 15))
        tx = _tx("-17.92", counterparty="Resend", tx_date=date(2026, 6, 18))

        matches = deterministic_match([inv], [tx], {})
        assert len(matches) == 1
        assert "conversion" in matches[0].rationale
        assert matches[0].confidence < Decimal("0.95")

    def test_fx_requires_a_vendor_name(self):
        """An implausible vendor is not rescued by a plausible rate."""
        inv = _inv("20.00", vendor="Resend", currency="USD",
                   invoice_date=date(2026, 6, 15))
        tx = _tx("-17.92", counterparty="The Burger Room", tx_date=date(2026, 6, 18))

        assert deterministic_match([inv], [tx], {}) == []

    def test_fx_rejects_implausible_rate(self):
        """Right vendor, right window, but the amount is nowhere near."""
        inv = _inv("20.00", vendor="Resend", currency="USD",
                   invoice_date=date(2026, 6, 15))
        tx = _tx("-4.10", counterparty="Resend", tx_date=date(2026, 6, 18))

        assert deterministic_match([inv], [tx], {}) == []

    def test_exact_amount_beats_fx_guess(self):
        """When the bank reports the original amount, the exact pair wins."""
        inv = _inv("20.00", vendor="Vercel", currency="USD",
                   invoice_date=date(2026, 6, 5))
        exact = _tx("-17.34", counterparty="Vercel", tx_date=date(2026, 6, 10),
                    original_amount="20.00", original_currency="USD")
        guess = _tx("-17.50", counterparty="Vercel", tx_date=date(2026, 6, 9))

        matches = deterministic_match([inv], [exact, guess], {})
        assert len(matches) == 1
        assert matches[0].transaction_id == exact.id

    def test_eur_invoice_never_uses_fx_path(self):
        """A EUR invoice must still match on the exact amount only."""
        inv = _inv("20.00", vendor="Resend", currency="EUR",
                   invoice_date=date(2026, 6, 15))
        tx = _tx("-17.92", counterparty="Resend", tx_date=date(2026, 6, 18))

        assert deterministic_match([inv], [tx], {}) == []

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
