"""LLM service — Claude API for invoice extraction, statement parsing, matching."""

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


EXTRACTION_PROMPT = """\
You are an invoice data extractor. Extract the following fields from the invoice text below.
Return ONLY valid JSON, no markdown fences.

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
    data = json.loads(raw_text)

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


# ---------------------------------------------------------------------------
# Pipeline 02, step 2 — Statement parsing
# ---------------------------------------------------------------------------

STATEMENT_PARSING_PROMPT = """\
You are a bank statement parser. Extract all transactions from the bank statement text below.
Return ONLY a valid JSON array, no markdown fences.

Amount sign convention:
- Debits (money going out) must be NEGATIVE
- Credits (money coming in) must be POSITIVE
- If the statement uses separate debit/credit columns, convert: debit → negative, credit → positive
- If the statement uses unsigned amounts with a type indicator, infer the sign from the label

For each transaction, extract:
- tx_date: string (YYYY-MM-DD) — the booking/execution date
- value_date: string (YYYY-MM-DD) or null — the valeur/value date if present (the date the bank actually processes the funds, which may differ from the booking date)
- amount: number (negative = debit, positive = credit) — in the account's base currency (EUR)
- original_amount: number or null — if the transaction involved a currency conversion, this is the amount in the original foreign currency
- original_currency: string or null — ISO 4217 currency code of the original amount (e.g. "USD", "GBP") if different from EUR
- description: string (raw bank description text)
- counterparty: string (who the payment is to/from)
- counterparty_iban: string or null
- no_invoice: boolean — set to true if this transaction will never have a matching invoice (e.g. tax payments, VAT/BTW remittances, government charges, bank fees, interest, currency conversion fees, salary/payroll). Set to false for normal vendor payments.

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
    data = json.loads(raw_text)

    if not isinstance(data, list):
        raise ValueError("LLM did not return a JSON array")

    return [_validate_transaction(tx) for tx in data]


# ---------------------------------------------------------------------------
# Pipeline 02, step 3 — Invoice ↔ Transaction matching
# ---------------------------------------------------------------------------

MATCHING_PROMPT = """\
You are a financial reconciliation engine. Match invoices to bank transactions for the same period.

Rules:
- Match by amount, date proximity, vendor name similarity, and IBAN when available
- Use the vendor aliases to recognize bank description variants
- Each invoice should match at most one transaction and vice versa
- Only suggest matches you are reasonably confident about (confidence >= 0.5)
- Confidence is 0.00 to 1.00
- Date tolerance: the bank transaction date or value_date may differ from the invoice date by several days (processing delay). Allow up to 10 days difference.
- Currency conversion: if a transaction has original_amount and original_currency, the invoice amount may be in the original currency (e.g. USD) while the transaction amount is the EUR equivalent. Match on original_amount when the invoice currency differs from EUR.
- Conversion fees: foreign currency payments often have a separate small transaction for the conversion fee (typically €0.50–€2.00). When you see a main debit matching a foreign currency invoice followed by a small fee transaction with a similar date and description mentioning "conversion", "fee", "kosten", or "wisselkoers", group them together — match the main debit to the invoice and note the fee in the rationale.

Return ONLY a valid JSON array, no markdown fences. Each element:
- invoice_id: string (UUID of the invoice)
- transaction_id: string (UUID of the transaction)
- confidence: number (0.00 to 1.00)
- rationale: string (brief explanation of why this is a match)

Unmatched invoices:
{invoices_json}

Unmatched transactions:
{transactions_json}

Known vendor aliases:
{aliases_json}
"""


async def match_invoices_transactions(
    invoices: list[dict[str, Any]],
    transactions: list[dict[str, Any]],
    vendor_aliases: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Use Claude to match invoices against transactions. Returns match suggestions."""
    if not invoices or not transactions:
        return []

    client = _get_client()
    message = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[
            {
                "role": "user",
                "content": MATCHING_PROMPT.format(
                    invoices_json=json.dumps(invoices, default=str),
                    transactions_json=json.dumps(transactions, default=str),
                    aliases_json=json.dumps(vendor_aliases, default=str),
                ),
            },
        ],
    )

    raw_text = message.content[0].text
    data = json.loads(raw_text)

    if not isinstance(data, list):
        raise ValueError("LLM did not return a JSON array")

    validated: list[dict[str, Any]] = []
    for match in data:
        try:
            confidence = Decimal(str(match["confidence"]))
        except (InvalidOperation, KeyError, TypeError) as e:
            raise ValueError(f"Invalid confidence in match: {e}")

        validated.append(
            {
                "invoice_id": UUID(str(match["invoice_id"])),
                "transaction_id": UUID(str(match["transaction_id"])),
                "confidence": confidence,
                "rationale": str(match.get("rationale", "")),
            }
        )

    return validated
