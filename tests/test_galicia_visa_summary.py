from __future__ import annotations

from pathlib import Path

import pytest

from santander_visa_parser.galicia_visa_summary import (
    GaliciaVISASummary,
    datetime_from_yyyymmdd,
)


@pytest.fixture
def summary() -> GaliciaVISASummary:
    return GaliciaVISASummary()


# Purpose: verify the parser extracts Galicia VISA close dates from barcode-like text.
def test_parse_statement_context_parses_barcode_date(summary):
    context = summary.parse_statement_context("foo 202601089999H bar")

    assert context.close_date.isoformat() == "2026-01-08"


# Purpose: verify the parser fails clearly when the close-date marker is absent.
def test_parse_statement_context_raises_when_barcode_date_is_missing(summary):
    with pytest.raises(ValueError, match="Could not determine Galicia VISA statement closing date"):
        summary.parse_statement_context("missing barcode")


# Purpose: verify line normalization keeps non-empty lines with stable source indexes.
def test_normalize_lines_compacts_blank_rows(summary):
    assert summary.normalize_lines(["", " a  b ", "c"]) == [(2, "a b"), (3, "c")]


# Purpose: verify Galicia VISA never merges rows at the normalization stage.
def test_should_merge_with_previous_is_always_false(summary):
    assert summary.should_merge_with_previous("line", [], -1) is False


# Purpose: verify ARS rows parse description, installment, and reference correctly.
def test_parse_transaction_body_parses_ars_transaction(summary):
    transaction = summary.parse_transaction_body(
        body="* MERPAGO WOK 01/03 123456 1.234,56",
        source_file=Path("statement.pdf"),
        line="12-12-25 * MERPAGO WOK 01/03 123456 1.234,56",
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
    assert transaction.reference == "123456"
    assert transaction.currency == "ARS"
    assert transaction.amount == "1234.56"


# Purpose: verify rows with a second trailing amount are treated as USD-billed transactions.
def test_parse_transaction_body_parses_usd_transaction(summary):
    transaction = summary.parse_transaction_body(
        body="AMAZON 123456 1.234,56 12,34",
        source_file=Path("statement.pdf"),
        line="12-12-25 AMAZON 123456 1.234,56 12,34",
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
    assert transaction.ars_amount == ""


# Purpose: verify invalid or summary-like bodies are rejected cleanly.
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
        body="SALDO ANTERIOR 1.234,56",
        source_file=Path("statement.pdf"),
        line="01-01-26 SALDO ANTERIOR 1.234,56",
        line_no=2,
        day=1,
        month=1,
        year=2026,
        statement_close_date="2026-01-08",
        reference="",
    )

    assert invalid is None
    assert summary_row is None


# Purpose: verify full Galicia VISA parsing stays inside the detail section and de-duplicates rows.
def test_parse_transactions_parses_only_detail_rows(summary):
    text = "\n".join(
        [
            "202601089999H",
            "header row",
            "DETALLE DEL CONSUMO",
            "12-12-25 * MERPAGO WOK 01/03 123456 1.234,56",
            "12-12-25 * MERPAGO WOK 01/03 123456 1.234,56",
            "13-12-25 AMAZON 123456 1.234,56 12,34",
            "14-12-25 SALDO ANTERIOR 1.234,56",
        ]
    )

    rows = summary.parse_transactions(text, Path("statement.pdf"))
    ars_rows = summary.parse_transactions(text, Path("statement.pdf"), currency_filter="ARS")

    assert len(rows) == 2
    assert rows[0]["description"] == "MERPAGO WOK"
    assert rows[1]["currency"] == "USD"
    assert ars_rows == [rows[0]]


# Purpose: verify Galicia VISA classification and parsing helpers remain stable.
def test_galicia_visa_helpers(summary):
    assert summary.is_header_line("PAGINA 1") is True
    assert summary.is_summary_line("TOTAL A PAGAR") is True
    assert summary.month_name_to_number("12") == 12
    assert summary.month_name_to_number("dic.") == 12
    assert summary.split_core("MERPAGO WOK 01/03 123456") == ("MERPAGO WOK", "01/03", "123456")
    assert summary.split_core("MERPAGO WOK 1234567890 123456") == (
        "MERPAGO WOK",
        "",
        "1234567890 123456",
    )
    assert summary.parse_decimal("1.234,56-") == "-1234.56"
    assert summary.collapse_whitespace(" a   b ") == "a b"
    assert summary.normalize_text("Tarjeta crédito") == "TARJETA CREDITO"


# Purpose: verify Galicia VISA helper functions still reject invalid month strings.
def test_galicia_visa_month_name_to_number_rejects_unknown_month(summary):
    with pytest.raises(ValueError, match="Unknown month name"):
        summary.month_name_to_number("zzz")


# Purpose: verify the module-level YYYYMMDD helper returns the expected date object.
def test_datetime_from_yyyymmdd_parses_date():
    assert datetime_from_yyyymmdd("20260108").isoformat() == "2026-01-08"
