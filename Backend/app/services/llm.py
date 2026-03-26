import io
import json
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID

import anthropic
import pdfplumber

from app.config import settings

_client: anthropic.AsyncAnthropic | None = None


def _get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _client


import re


def _parse_json(text: str) -> Any:
    """Parse JSON from LLM output, stripping markdown fences if present."""
    text = text.strip()
    # Strip ```json ... ``` or ``` ... ```
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()
    return json.loads(text)


EXTRACTION_PROMPT = """\
You are an invoice data extractor. Extract the following fields from the invoice text below.
Return ONLY valid JSON.

Required fields:
- vendor: string — the company/business name that issued the invoice. This must be ONLY the company name (e.g. "Vercel", "AWS", "Google Cloud"). Do NOT include descriptions like "excl. VAT", amounts, or other text.
- invoice_number: string
- invoice_date: string (YYYY-MM-DD)
- amount_excl: number (amount excluding VAT)
- amount_incl: number (amount including VAT)
- vat_amount: number
- vat_rate: number (e.g. 21.0 for 21%)
- currency: string (e.g. "EUR")
- iban: string or null
- category: string — classify the expense into one of: "SaaS", "Infrastructure", "Marketing", "Legal", "Accounting", "Insurance", "Office", "Travel", "Telecom", "Freelancers", "Other". Pick the best fit based on the vendor and invoice contents.

Invoice text:
{text}
"""


async def extract_invoice_from_pdf(pdf_bytes: bytes) -> dict[str, Any]:
    """Extract structured invoice data from a PDF using pdfplumber + Claude."""
    text = ""
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"

    if not text.strip():
        raise ValueError("Could not extract text from PDF")

    client = _get_client()
    message = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[
            {"role": "user", "content": EXTRACTION_PROMPT.format(text=text)},
        ],
    )

    raw_text = message.content[0].text
    data = _parse_json(raw_text)

    return {
        "vendor": data["vendor"],
        "invoice_number": data["invoice_number"],
        "invoice_date": date.fromisoformat(data["invoice_date"]),
        "amount_excl": Decimal(str(data["amount_excl"])),
        "amount_incl": Decimal(str(data["amount_incl"])),
        "vat_amount": Decimal(str(data["vat_amount"])),
        "vat_rate": Decimal(str(data["vat_rate"])),
        "category": data.get("category"),
        "raw": data,
    }


STATEMENT_PARSING_PROMPT = """\
Extract all transactions from the bank statement below. Return ONLY a valid JSON array.

Amounts: debits NEGATIVE, credits POSITIVE.
Sign hints: Χ/Χρέωση/D/Debet/AF = negative; Π/Πίστωση/C/Credit/BIJ = positive.

Fields per transaction:
  tx_date        string YYYY-MM-DD (booking date)
  value_date     string YYYY-MM-DD | null
  amount         number in EUR (signed)
  original_amount  number | null (foreign currency amount if converted)
  original_currency  string ISO 4217 | null
  description    string (raw bank text)
  counterparty   string
  counterparty_iban  string | null
  no_invoice     bool — true for expenses that never have invoices (taxes, bank fees, interest, FX fees, government charges). Always false for credits/earnings.
  withholding    bool — true for owner drawings against earnings (e.g. "ΕΝΑΝΤΙ ΚΕΡΔΩΝ", "ΑΝΑΛΗΨΗ ΕΝΑΝΤΙ"). Not taxes or fees.
  category       string | null — one of: Tax, VAT, Bank Fee, Insurance, Salary, Interest, Currency Conversion, Government, SaaS, Infrastructure, Marketing, Legal, Accounting, Office, Travel, Telecom, Freelancers, Other. Required when no_invoice=true, optional otherwise.

Bank statement text:
{text}
"""


def _validate_transaction(tx: dict[str, Any]) -> dict[str, Any]:
    """Type-cast and validate a single parsed transaction."""
    # Required fields
    for field in ("tx_date", "amount", "description", "counterparty"):
        if field not in tx or tx[field] is None:
            raise ValueError(f"Missing required field: {field}")

    try:
        tx_date = date.fromisoformat(str(tx["tx_date"]))
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid tx_date '{tx['tx_date']}': {e}")

    try:
        amount = Decimal(str(tx["amount"]))
    except (InvalidOperation, TypeError) as e:
        raise ValueError(f"Invalid amount '{tx['amount']}': {e}")

    # Optional value_date
    value_date = None
    if tx.get("value_date"):
        try:
            value_date = date.fromisoformat(str(tx["value_date"]))
        except (ValueError, TypeError):
            pass

    # Optional original amount + currency (foreign currency conversion)
    original_amount = None
    if tx.get("original_amount") is not None:
        try:
            original_amount = Decimal(str(tx["original_amount"]))
        except (InvalidOperation, TypeError):
            pass

    original_currency = tx.get("original_currency")

    return {
        "tx_date": tx_date,
        "value_date": value_date,
        "amount": amount,
        "original_amount": original_amount,
        "original_currency": original_currency,
        "description": str(tx["description"]),
        "counterparty": str(tx["counterparty"]),
        "counterparty_iban": tx.get("counterparty_iban"),
        "no_invoice": bool(tx.get("no_invoice", False)),
        "withholding": bool(tx.get("withholding", False)),
        "category": tx.get("category"),
    }


async def parse_bank_statement(statement_text: str) -> list[dict[str, Any]]:
    """Parse a bank statement text into a list of validated transactions."""
    if not statement_text.strip():
        raise ValueError("Empty statement text")

    client = _get_client()
    message = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[
            {
                "role": "user",
                "content": STATEMENT_PARSING_PROMPT.format(text=statement_text),
            },
        ],
    )

    raw_text = message.content[0].text
    data = _parse_json(raw_text)

    if not isinstance(data, list):
        raise ValueError("LLM did not return a JSON array")

    return [_validate_transaction(tx) for tx in data]

SINGLE_MATCH_PROMPT = """\
Does this invoice match any of these bank transactions?

Invoice:
- vendor: {vendor}
- amount: {amount} {currency}
- date: {invoice_date}

Bank transactions:
{transactions_json}

Rules:
- The transaction amount is in EUR. If the invoice is in another currency, \
check if the EUR amount is plausible given typical exchange rates.
- The transaction date may differ from the invoice date by up to 10 days.
- Only match if the vendor/counterparty clearly refers to the same company.
- If no transaction matches, return an empty array [].

Return ONLY valid JSON, no markdown fences:
[{{"transaction_id": "...", "confidence": 0.00-1.00, "rationale": "..."}}]
or [] if no match.
"""


async def match_single_invoice(
    invoice: dict[str, Any],
    transactions: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Ask the LLM to find a matching transaction for a single invoice."""
    if not transactions:
        return None

    client = _get_client()
    message = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=512,
        messages=[
            {
                "role": "user",
                "content": SINGLE_MATCH_PROMPT.format(
                    vendor=invoice["vendor"],
                    amount=invoice["amount_incl"],
                    currency=invoice.get("currency", "EUR"),
                    invoice_date=invoice["invoice_date"],
                    transactions_json=json.dumps(transactions, default=str),
                ),
            },
        ],
    )

    raw_text = message.content[0].text
    data = _parse_json(raw_text)

    if not isinstance(data, list) or len(data) == 0:
        return None

    match = data[0]
    try:
        confidence = Decimal(str(match["confidence"]))
    except (InvalidOperation, KeyError, TypeError):
        return None

    if confidence < Decimal("0.5"):
        return None

    return {
        "invoice_id": UUID(str(invoice["id"])),
        "transaction_id": UUID(str(match["transaction_id"])),
        "confidence": confidence,
        "rationale": str(match.get("rationale", "")),
    }
