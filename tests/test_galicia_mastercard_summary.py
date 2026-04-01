from __future__ import annotations

from pathlib import Path

import pytest

from santander_visa_parser.galicia_mastercard_summary import GaliciaMastercardSummary


@pytest.fixture
def summary() -> GaliciaMastercardSummary:
    return GaliciaMastercardSummary()


# Purpose: verify the parser extracts Galicia Mastercard close dates from barcode-like text.
def test_parse_statement_context_parses_barcode_date(summary):
    context = summary.parse_statement_context("foo 202601089999H bar")

    assert context.close_date.isoformat() == "2026-01-08"


# Purpose: verify missing close-date markers raise a precise error.
def test_parse_statement_context_raises_when_barcode_date_is_missing(summary):
    with pytest.raises(ValueError, match="Could not determine Galicia Mastercard statement closing date"):
        summary.parse_statement_context("missing barcode")


# Purpose: verify normalization keeps only non-empty compacted lines.
def test_normalize_lines_compacts_blank_rows(summary):
    assert summary.normalize_lines(["", " a  b ", "c"]) == [(2, "a b"), (3, "c")]


# Purpose: verify Galicia Mastercard never merges rows while normalizing.
def test_should_merge_with_previous_is_always_false(summary):
    assert summary.should_merge_with_previous("line", [], -1) is False


# Purpose: verify ARS rows parse description, installment, and reference via the core matcher.
def test_parse_transaction_body_parses_ars_transaction(summary):
    transaction = summary.parse_transaction_body(
        body="MERPAGO WOK 01/03 REF123 1.234,56",
        source_file=Path("statement.pdf"),
        line="12-DIC-25 MERPAGO WOK 01/03 REF123 1.234,56",
        line_no=10,
        day=12,
        month=12,
        year=2025,
        statement_close_date="2026-01-08",
        reference="",
    )

    assert transaction is not None
    assert transaction.description == "MERPAGO WOK"
    assert transaction.installment == "01/03"
    assert transaction.reference == "REF123"
    assert transaction.currency == "ARS"
    assert transaction.amount == "1234.56"


# Purpose: verify foreign information and second billed amount produce a USD transaction.
def test_parse_transaction_body_parses_usd_transaction(summary):
    transaction = summary.parse_transaction_body(
        body="AMAZON (USA,USD, 10,00) REF123 1.234,56 12,34",
        source_file=Path("statement.pdf"),
        line="12-DIC-25 AMAZON (USA,USD, 10,00) REF123 1.234,56 12,34",
        line_no=11,
        day=12,
        month=12,
        year=2025,
        statement_close_date="2026-01-08",
        reference="",
    )

    assert transaction is not None
    assert transaction.currency == "USD"
    assert transaction.amount == "12.34"
    assert transaction.usd_amount == "12.34"
    assert transaction.original_currency == "USD"
    assert transaction.original_amount == "10.00"
    assert transaction.reference == "REF123"


# Purpose: verify invalid or summary-like rows are rejected instead of misparsed.
def test_parse_transaction_body_rejects_invalid_and_summary_rows(summary):
    invalid = summary.parse_transaction_body(
        body="bad row",
        source_file=Path("statement.pdf"),
        line="bad row",
        line_no=1,
        day=1,
        month=1,
        year=2026,
        statement_close_date="2026-01-08",
        reference="",
    )
    summary_row = summary.parse_transaction_body(
        body="SALDO ANTERIOR REF123 1.234,56",
        source_file=Path("statement.pdf"),
        line="01-ENE-26 SALDO ANTERIOR REF123 1.234,56",
        line_no=2,
        day=1,
        month=1,
        year=2026,
        statement_close_date="2026-01-08",
        reference="",
    )

    assert invalid is None
    assert summary_row is None


# Purpose: verify full Galicia Mastercard parsing stops at the ending section and de-duplicates rows.
def test_parse_transactions_parses_only_detail_rows(summary):
    text = "\n".join(
        [
            "202601089999H",
            "DETALLE DEL CONSUMO",
            "12-DIC-25 MERPAGO WOK 01/03 REF123 1.234,56",
            "12-DIC-25 MERPAGO WOK 01/03 REF123 1.234,56",
            "13-DIC-25 AMAZON (USA,USD, 10,00) REF123 1.234,56 12,34",
            "CUOTAS A VENCER",
            "14-DIC-25 SHOULD NOT PARSE REF999 1.000,00",
        ]
    )

    rows = summary.parse_transactions(text, Path("statement.pdf"))
    usd_rows = summary.parse_transactions(text, Path("statement.pdf"), currency_filter="USD")

    assert len(rows) == 2
    assert rows[0]["description"] == "MERPAGO WOK"
    assert rows[1]["currency"] == "USD"
    assert usd_rows == [rows[1]]


# Purpose: verify Galicia Mastercard helper methods keep their parsing rules stable.
def test_galicia_mastercard_helpers(summary):
    assert summary.is_header_line("COMPRAS DEL MES") is True
    assert summary.is_summary_line("TOTAL A PAGAR") is True
    assert summary.month_name_to_number("dic") == 12
    assert summary.parse_decimal("1.234,56-") == "-1234.56"
    assert summary.collapse_whitespace(" a   b ") == "a b"
    assert summary.normalize_text("Tarjeta crédito") == "TARJETA CREDITO"


# Purpose: verify invalid month names are rejected instead of producing wrong dates.
def test_galicia_mastercard_month_name_to_number_rejects_unknown_month(summary):
    with pytest.raises(ValueError, match="Unknown month name"):
        summary.month_name_to_number("zzz")
