"""StatementIngester — converts bank statement files to clean text for LLM parsing.

Supported formats:
- XLS / XLSX → CSV string via openpyxl
- MT940 → structured text via mt940 lib
- CAMT.053 → structured text via XML parse
- CSV → decoded text (pass-through with encoding detection)
"""

import csv
import io
import xml.etree.ElementTree as ET

import mt940
import openpyxl


def ingest(file_bytes: bytes, filename: str) -> str:
    """Route to the correct parser based on file extension. Returns clean text."""
    name_lower = filename.lower()

    if name_lower.endswith((".xls", ".xlsx")):
        return ingest_xlsx(file_bytes)
    elif name_lower.endswith(".mt940") or name_lower.endswith(".sta"):
        return ingest_mt940(file_bytes)
    elif name_lower.endswith(".xml"):
        return ingest_camt053(file_bytes)
    elif name_lower.endswith(".csv"):
        return ingest_csv(file_bytes)
    else:
        raise ValueError(f"Unsupported file format: {filename}")


def ingest_xlsx(file_bytes: bytes) -> str:
    """Convert XLS/XLSX to CSV string via openpyxl."""
    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
    output = io.StringIO()
    writer = csv.writer(output)

    ws = wb.active
    for row in ws.iter_rows(values_only=True):
        # Convert None to empty string for CSV
        writer.writerow([cell if cell is not None else "" for cell in row])

    wb.close()
    return output.getvalue()


def ingest_mt940(file_bytes: bytes) -> str:
    """Convert MT940 to structured text via mt940 lib.

    mt940.parse() returns a Transactions object that iterates over
    Transaction objects directly. Each Transaction has .data with
    fields like amount, date, customer_reference, transaction_details.
    The parent statement info is on tx.transactions.
    """
    parsed = mt940.parse(io.BytesIO(file_bytes))
    lines: list[str] = []

    for tx in parsed:
        amount = tx.data.get("amount")
        date_val = tx.data.get("date")
        customer_ref = tx.data.get("customer_reference", "")
        details = tx.data.get("transaction_details", "")

        lines.append(f"Date: {date_val}")
        lines.append(f"Amount: {amount}")
        if customer_ref:
            lines.append(f"Counterparty: {customer_ref}")
        if details:
            lines.append(f"Description: {details}")
        lines.append("---")

    return "\n".join(lines)


def ingest_camt053(file_bytes: bytes) -> str:
    """Convert CAMT.053 XML to structured text."""
    root = ET.fromstring(file_bytes)

    # CAMT.053 uses a namespace — detect it from root tag
    ns = ""
    if root.tag.startswith("{"):
        ns = root.tag.split("}")[0] + "}"

    lines: list[str] = []

    # Find all entries (Ntry elements)
    for stmt in root.iter(f"{ns}Stmt"):
        acct = stmt.find(f"{ns}Acct/{ns}Id/{ns}IBAN")
        if acct is not None:
            lines.append(f"Account IBAN: {acct.text}")
            lines.append("")

        for entry in stmt.iter(f"{ns}Ntry"):
            amount_el = entry.find(f"{ns}Amt")
            amount = amount_el.text if amount_el is not None else ""
            currency = amount_el.get("Ccy", "") if amount_el is not None else ""

            cdt_dbt = entry.find(f"{ns}CdtDbtInd")
            direction = cdt_dbt.text if cdt_dbt is not None else ""

            booking_date = entry.find(f"{ns}BookgDt/{ns}Dt")
            date_text = booking_date.text if booking_date is not None else ""

            # Get transaction details
            details = entry.find(f"{ns}NtryDtls/{ns}TxDtls")
            counterparty_name = ""
            counterparty_iban = ""
            description = ""

            if details is not None:
                # Related parties
                if direction == "DBIT":
                    party = details.find(f"{ns}RltdPties/{ns}Cdtr/{ns}Nm")
                    iban = details.find(f"{ns}RltdPties/{ns}CdtrAcct/{ns}Id/{ns}IBAN")
                else:
                    party = details.find(f"{ns}RltdPties/{ns}Dbtr/{ns}Nm")
                    iban = details.find(f"{ns}RltdPties/{ns}DbtrAcct/{ns}Id/{ns}IBAN")

                if party is not None:
                    counterparty_name = party.text
                if iban is not None:
                    counterparty_iban = iban.text

                # Remittance info
                rmt = details.find(f"{ns}RmtInf/{ns}Ustrd")
                if rmt is not None:
                    description = rmt.text

            sign = "-" if direction == "DBIT" else ""
            lines.append(f"Date: {date_text}")
            lines.append(f"Amount: {sign}{amount} {currency}")
            lines.append(f"Direction: {direction}")
            if counterparty_name:
                lines.append(f"Counterparty: {counterparty_name}")
            if counterparty_iban:
                lines.append(f"IBAN: {counterparty_iban}")
            if description:
                lines.append(f"Description: {description}")
            lines.append("---")

    return "\n".join(lines)


def ingest_csv(file_bytes: bytes) -> str:
    """Decode CSV bytes to text. Tries UTF-8 first, falls back to latin-1."""
    try:
        return file_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        return file_bytes.decode("latin-1")
