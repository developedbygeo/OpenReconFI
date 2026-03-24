"""Example portal scraper — documented reference implementation.

This demonstrates how to build a scraper for a supplier portal using Playwright.
Copy this file and adapt it for each real supplier.

Usage:
    scraper = ExampleSupplierScraper(username="user", password="pass")
    await scraper.login()
    invoices = await scraper.scrape()
    await scraper.close()
"""

from playwright.async_api import async_playwright

from app.scrapers.base import PortalScraper, ScrapedInvoice


class ExampleSupplierScraper(PortalScraper):
    """Reference scraper for 'Example Supplier Co.'

    Portal URL: https://portal.example-supplier.com
    Login: email + password form
    Invoice list: /invoices page with download links
    """

    PORTAL_URL = "https://portal.example-supplier.com"

    def __init__(self, username: str, password: str) -> None:
        self.username = username
        self.password = password
        self._playwright = None
        self._browser = None
        self._page = None

    async def login(self) -> None:
        """Launch browser and authenticate with the portal."""
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=True)
        self._page = await self._browser.new_page()

        await self._page.goto(f"{self.PORTAL_URL}/login")
        await self._page.fill('input[name="email"]', self.username)
        await self._page.fill('input[name="password"]', self.password)
        await self._page.click('button[type="submit"]')
        await self._page.wait_for_url(f"{self.PORTAL_URL}/dashboard")

    async def scrape(self) -> list[ScrapedInvoice]:
        """Navigate to invoices page and download each PDF."""
        if not self._page:
            raise RuntimeError("Must call login() before scrape()")

        await self._page.goto(f"{self.PORTAL_URL}/invoices")

        rows = await self._page.query_selector_all("table.invoices tbody tr")
        results: list[ScrapedInvoice] = []

        for row in rows:
            cells = await row.query_selector_all("td")
            if len(cells) < 6:
                continue

            invoice_number = (await cells[0].inner_text()).strip()
            invoice_date = (await cells[1].inner_text()).strip()
            vendor = (await cells[2].inner_text()).strip()
            amount_excl = (await cells[3].inner_text()).strip()
            vat_amount = (await cells[4].inner_text()).strip()
            amount_incl = (await cells[5].inner_text()).strip()

            download_link = await row.query_selector("a.download-pdf")
            if not download_link:
                continue

            async with self._page.expect_download() as download_info:
                await download_link.click()
            download = await download_info.value
            pdf_path = await download.path()

            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()

            results.append(
                ScrapedInvoice(
                    vendor=vendor,
                    invoice_number=invoice_number,
                    invoice_date=invoice_date,
                    amount_excl=amount_excl,
                    amount_incl=amount_incl,
                    vat_amount=vat_amount,
                    vat_rate="21.00",
                    pdf_bytes=pdf_bytes,
                    filename=f"{invoice_number}.pdf",
                )
            )

        return results

    async def close(self) -> None:
        """Close browser and Playwright."""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
