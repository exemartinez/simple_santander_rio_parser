from __future__ import annotations

from pathlib import Path

import pytest

from santander_visa_parser.santander_rio_visa_summary import SantanderRioVISASummary


@pytest.fixture
def summary() -> SantanderRioVISASummary:
    return SantanderRioVISASummary()


# Purpose: verify the parser extracts the close date from the modern Santander header.
def test_parse_statement_context_parses_named_month(summary):
    context = summary.parse_statement_context("CIERRE 08 Enero 26")

    assert context.close_date.isoformat() == "2026-01-08"


# Purpose: verify the parser still supports the older numeric close-date format.
def test_parse_statement_context_parses_legacy_date(summary):
    context = summary.parse_statement_context("Resumen 08-01-2026")

    assert context.close_date.isoformat() == "2026-01-08"


# Purpose: verify missing close-date information raises an explicit error.
def test_parse_statement_context_raises_when_date_is_missing(summary):
    with pytest.raises(ValueError, match="Could not determine statement closing date"):
        summary.parse_statement_context("no date here")


# Purpose: verify line normalization merges PDF spillover text into the preceding transaction row.
def test_normalize_lines_merges_continuation_lines(summary):
    lines = [
        "13 001664 * MOVISTAR",
        "DA 000000013769984 43.839,96",
        "",
        "________________",
    ]

    assert summary.normalize_lines(lines) == [
        (1, "13 001664 * MOVISTAR DA 000000013769984 43.839,96")
    ]


# Purpose: verify merge heuristics stay conservative for new rows and permissive for continuations.
def test_should_merge_with_previous_distinguishes_continuations(summary):
    merged = [(1, "13 001664 * MOVISTAR")]

    assert summary.should_merge_with_previous("continuation text", merged, 0) is True
    assert summary.should_merge_with_previous("14 123456 * NEW ROW", merged, 0) is False
    assert summary.should_merge_with_previous("SALDO ANTERIOR", merged, 0) is False


# Purpose: verify ARS transaction bodies are normalized into the shared transaction shape.
def test_parse_transaction_body_parses_ars_transaction(summary):
    transaction = summary.parse_transaction_body(
        body="MERPAGO*WOK C.05/18 1.421,34",
        source_file=Path("statement.pdf"),
        line="25 Diciem. 20 966693 * MERPAGO*WOK C.05/18 1.421,34",
        line_no=33,
        day=20,
        month=12,
        year=2025,
        statement_close_date="2026-01-08",
        reference="966693",
    )

    assert transaction is not None
    assert transaction.description == "MERPAGO*WOK"
    assert transaction.currency == "ARS"
    assert transaction.amount == "1421.34"
    assert transaction.ars_amount == "1421.34"
    assert transaction.installment == "C.05/18"
    assert transaction.reference == "966693"


# Purpose: verify foreign currency transaction bodies preserve billed and original amounts.
def test_parse_transaction_body_parses_foreign_transaction(summary):
    transaction = summary.parse_transaction_body(
        body="GOOGLE *YouTubeP USD 4,73 4,73",
        source_file=Path("statement.pdf"),
        line="21 829935 GOOGLE *YouTubeP USD 4,73 4,73",
        line_no=87,
        day=21,
        month=12,
        year=2025,
        statement_close_date="2026-01-08",
        reference="829935",
    )

    assert transaction is not None
    assert transaction.currency == "USD"
    assert transaction.amount == "4.73"
    assert transaction.usd_amount == "4.73"
    assert transaction.original_currency == "USD"
    assert transaction.original_amount == "4.73"


# Purpose: verify non-transaction bodies and summary markers are rejected.
def test_parse_transaction_body_returns_none_for_invalid_or_summary_rows(summary):
    invalid = summary.parse_transaction_body(
        body="not a transaction",
        source_file=Path("statement.pdf"),
        line="not a transaction",
        line_no=1,
        day=1,
        month=1,
        year=2026,
        statement_close_date="2026-01-08",
        reference="",
    )
    summary_row = summary.parse_transaction_body(
        body="SALDO ANTERIOR 10,00",
        source_file=Path("statement.pdf"),
        line="01 SALDO ANTERIOR 10,00",
        line_no=2,
        day=1,
        month=1,
        year=2026,
        statement_close_date="2026-01-08",
        reference="",
    )

    assert invalid is None
    assert summary_row is None


# Purpose: verify full Santander parsing handles month inference, de-duplication, and currency filtering.
def test_parse_transactions_normalizes_statement_text(summary):
    text = "\n".join(
        [
            "CIERRE 08 Enero 26",
            "25 Diciem. 20 966693 * MERPAGO*WOK C.05/18 1.421,34",
            "13 775290 GOOGLE *YouTubeP USD 4,73 4,73",
            "13 775290 GOOGLE *YouTubeP USD 4,73 4,73",
            "13 SALDO ANTERIOR 10,00",
        ]
    )

    rows = summary.parse_transactions(text, Path("statement.pdf"))
    usd_rows = summary.parse_transactions(text, Path("statement.pdf"), currency_filter="USD")

    assert len(rows) == 2
    assert [row["transaction_date"] for row in rows] == ["2025-12-13", "2025-12-20"]
    assert [row["currency"] for row in rows] == ["USD", "ARS"]
    assert usd_rows == [rows[0]]


# Purpose: verify simple classification helpers stay aligned with Santander line filters.
def test_santander_line_classification_and_helpers(summary):
    assert summary.is_header_line("VISA") is True
    assert summary.is_summary_line("SALDO ANTERIOR") is True
    assert summary.normalize_currency("U$S") == "USD"
    assert summary.parse_decimal("1.421,34-") == "-1421.34"
    assert summary.month_name_to_number("Diciem.") == 12
    assert summary.collapse_whitespace(" a   b ") == "a b"
    assert summary.normalize_text("Santander Río") == "SANTANDER RIO"


# Purpose: verify invalid month names still fail instead of silently corrupting dates.
def test_santander_month_name_to_number_rejects_unknown_month(summary):
    with pytest.raises(ValueError, match="Unknown month name"):
        summary.month_name_to_number("zzz")
