import pytest

from app.services.dedup import normalize_invoice_number


class TestNormalizeInvoiceNumber:
    @pytest.mark.parametrize(
        "a,b",
        [
            # Separator drift between extraction runs
            ("U5YB9SXN 0001", "U5YB9SXN-0001"),
            ("0XWURR8N 0013", "0XWURR8N-0013"),
            ("15FE322D 0061", "15FE322D-0061"),
            # Greek homoglyph: Greek rho vs Latin P
            ("070Ρ-805091", "070P-805091"),
            # Greek transliterated to Latin
            ("ΤΔΑ-Α-09490", "TDA-A-09490"),
            ("ΤΔΑ-SKZ-62627", "TDA-SKZ-62627"),
            # Case drift
            ("inv-00211", "INV-00211"),
        ],
    )
    def test_drift_variants_normalize_equal(self, a: str, b: str) -> None:
        assert normalize_invoice_number(a) == normalize_invoice_number(b)

    def test_distinct_numbers_stay_distinct(self) -> None:
        assert normalize_invoice_number("541788894") != normalize_invoice_number("544572563")
        assert normalize_invoice_number("INV-00211") != normalize_invoice_number("INV-00212")

    def test_strips_separators(self) -> None:
        assert normalize_invoice_number("ΤΔΑ-Α-09490") == "TDAA09490"
        assert normalize_invoice_number("INV-00211") == "INV00211"

    def test_empty_when_no_alphanumerics(self) -> None:
        assert normalize_invoice_number("---") == ""
        assert normalize_invoice_number("") == ""
