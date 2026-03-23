"""Abstract base class for portal scrapers."""

import abc
from dataclasses import dataclass


@dataclass
class ScrapedInvoice:
    """Data extracted from a supplier portal."""

    vendor: str
    invoice_number: str
    invoice_date: str
    amount_excl: str
    amount_incl: str
    vat_amount: str
    vat_rate: str
    pdf_bytes: bytes
    filename: str


class PortalScraper(abc.ABC):
    """Base class for all portal scrapers.

    Subclasses must implement `login()` and `scrape()`.
    The collector calls `login()` once, then `scrape()` to fetch new invoices.
    """

    @abc.abstractmethod
    async def login(self) -> None:
        """Authenticate with the supplier portal."""
        ...

    @abc.abstractmethod
    async def scrape(self) -> list[ScrapedInvoice]:
        """Fetch all new/unprocessed invoices from the portal.

        Returns a list of ScrapedInvoice with PDF bytes and metadata.
        """
        ...

    async def close(self) -> None:
        """Clean up resources (browser, session, etc.). Override if needed."""
        pass
