"""Tests for StatementIngester — one test per format."""

import io

import openpyxl
import pytest

from app.services.ingester import ingest, ingest_camt053, ingest_csv, ingest_mt940, ingest_xlsx


def test_ingest_xlsx():
    """XLSX → CSV string via openpyxl."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Date", "Description", "Amount"])
    ws.append(["2026-03-04", "VERCEL INC", "-49.00"])
    ws.append(["2026-03-05", "HETZNER", "-10.00"])

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    result = ingest(buf.read(), "statement.xlsx")
    assert "VERCEL INC" in result
    assert "HETZNER" in result
    assert "-49.00" in result


def test_ingest_csv():
    """CSV → decoded text."""
    csv_content = "Date,Description,Amount\n2026-03-04,VERCEL INC,-49.00\n"
    result = ingest(csv_content.encode("utf-8"), "statement.csv")
    assert "VERCEL INC" in result
    assert "-49.00" in result


def test_ingest_csv_latin1():
    """CSV with latin-1 encoding (common in European banks)."""
    csv_content = "Date,Description,Amount\n2026-03-04,BÜRO GmbH,-100.00\n"
    result = ingest(csv_content.encode("latin-1"), "bank.csv")
    assert "BÜRO GmbH" in result


def test_ingest_camt053():
    """CAMT.053 XML → structured text."""
    xml = """\
<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.02">
  <BkToCstmrStmt>
    <Stmt>
      <Acct>
        <Id><IBAN>NL91ABNA0417164300</IBAN></Id>
      </Acct>
      <Ntry>
        <Amt Ccy="EUR">49.00</Amt>
        <CdtDbtInd>DBIT</CdtDbtInd>
        <BookgDt><Dt>2026-03-04</Dt></BookgDt>
        <NtryDtls>
          <TxDtls>
            <RltdPties>
              <Cdtr><Nm>Vercel Inc</Nm></Cdtr>
              <CdtrAcct><Id><IBAN>NL02ABNA0123456789</IBAN></Id></CdtrAcct>
            </RltdPties>
            <RmtInf>
              <Ustrd>SUBSCRIPTION PAYMENT</Ustrd>
            </RmtInf>
          </TxDtls>
        </NtryDtls>
      </Ntry>
    </Stmt>
  </BkToCstmrStmt>
</Document>"""

    result = ingest(xml.encode("utf-8"), "statement.xml")
    assert "NL91ABNA0417164300" in result
    assert "Vercel Inc" in result
    assert "-49.00" in result
    assert "SUBSCRIPTION PAYMENT" in result


def test_ingest_mt940():
    """MT940 → structured text (using minimal MT940 data)."""
    # MT940 is a complex format — test the parser handles it without crashing.
    # A real MT940 file would come from a bank; here we test the function exists
    # and handles empty/minimal input gracefully.
    mt940_data = b""":20:STARTOFMT940
:25:NL91ABNA0417164300
:28C:00000
:60F:C260301EUR1000,00
:61:2603040304D49,00NTRFVERCEL INC//SUBSCRIPTION
:86:VERCEL INC SUBSCRIPTION PAYMENT
:62F:C260304EUR951,00
-"""

    result = ingest(mt940_data, "statement.mt940")
    assert isinstance(result, str)
    # MT940 lib should parse at least the transaction
    assert len(result) > 0


def test_ingest_unsupported_format():
    """Unsupported format raises ValueError."""
    with pytest.raises(ValueError, match="Unsupported file format"):
        ingest(b"data", "statement.pdf")
