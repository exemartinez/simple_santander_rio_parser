from __future__ import annotations

from pathlib import Path

import pytest

from santander_visa_parser.mercadopago_account_summary import MercadoPagoAccountSummary


@pytest.fixture
def summary() -> MercadoPagoAccountSummary:
    return MercadoPagoAccountSummary()


# Purpose: verify the parser extracts the statement period end date from MercadoPago text.
def test_parse_statement_context_parses_period(summary):
    context = summary.parse_statement_context("Período Del 1 al 31 de Enero de 2026")

    assert context.close_date.isoformat() == "2026-01-31"


# Purpose: verify missing statement period data raises a precise error.
def test_parse_statement_context_raises_when_period_is_missing(summary):
    with pytest.raises(ValueError, match="Could not determine MercadoPago statement period"):
        summary.parse_statement_context("missing period")


# Purpose: verify normalization starts after the detail header and merges multiline descriptions.
def test_normalize_lines_merges_multiline_transactions(summary):
    lines = [
        "1/2",
        "DETALLE DE MOVIMIENTOS",
        "FECHA DESCRIPCION ID DE LA OPERACION VALOR SALDO",
        "01-01-2026 Compra",
        "en dos partes 123456789 $ 1.234,56 $ 9.999,99",
        "02-01-2026 Otra compra 987654321 $ 50,00 $ 9.949,99",
    ]

    assert summary.normalize_lines(lines) == [
        (4, "01-01-2026 Compra en dos partes 123456789 $ 1.234,56 $ 9.999,99"),
        (6, "02-01-2026 Otra compra 987654321 $ 50,00 $ 9.949,99"),
    ]


# Purpose: verify MercadoPago never uses the generic merge hook.
def test_should_merge_with_previous_is_always_false(summary):
    assert summary.should_merge_with_previous("line", [], -1) is False


# Purpose: verify MercadoPago rows are normalized as ARS movements with signed ars_amount.
def test_parse_transaction_body_parses_account_movement(summary):
    transaction = summary.parse_transaction_body(
        body="Compra 123456789 $ 1.234,56 $ 9.999,99",
        source_file=Path("statement.pdf"),
        line="01-01-2026 Compra 123456789 $ 1.234,56 $ 9.999,99",
        line_no=4,
        day=1,
        month=1,
        year=2026,
        statement_close_date="2026-01-31",
        reference="",
    )

    assert transaction is not None
    assert transaction.description == "Compra"
    assert transaction.currency == "ARS"
    assert transaction.amount == "1234.56"
    assert transaction.ars_amount == "-1234.56"
    assert transaction.reference == "123456789"


# Purpose: verify invalid account movement rows are rejected cleanly.
def test_parse_transaction_body_rejects_invalid_rows(summary):
    transaction = summary.parse_transaction_body(
        body="bad row",
        source_file=Path("statement.pdf"),
        line="bad row",
        line_no=1,
        day=1,
        month=1,
        year=2026,
        statement_close_date="2026-01-31",
        reference="",
    )

    assert transaction is None


# Purpose: verify full MercadoPago parsing de-duplicates movements and respects currency filters.
def test_parse_transactions_parses_detail_rows(summary):
    text = "\n".join(
        [
            "Período Del 1 al 31 de Enero de 2026",
            "DETALLE DE MOVIMIENTOS",
            "01-01-2026 Compra 123456789 $ 1.234,56 $ 9.999,99",
            "01-01-2026 Compra 123456789 $ 1.234,56 $ 9.999,99",
            "02-01-2026 Otra compra 987654321 $ 50,00 $ 9.949,99",
        ]
    )

    rows = summary.parse_transactions(text, Path("statement.pdf"))
    usd_rows = summary.parse_transactions(text, Path("statement.pdf"), currency_filter="USD")

    assert len(rows) == 2
    assert rows[0]["transaction_date"] == "2026-01-01"
    assert rows[1]["description"] == "Otra compra"
    assert usd_rows == []


# Purpose: verify MercadoPago helper methods preserve month, decimal, and normalization rules.
def test_mercadopago_helpers(summary):
    assert summary.is_header_line("CVU: 123") is True
    assert summary.is_summary_line("anything") is False
    assert summary.month_name_to_number("Enero") == 1
    assert summary.parse_decimal("1.234,56-") == "-1234.56"
    assert summary.negate_decimal_string("1234.56") == "-1234.56"
    assert summary.collapse_whitespace(" a   b ") == "a b"
    assert summary.normalize_text("Período") == "PERIODO"


# Purpose: verify invalid month names still fail fast in MercadoPago statements.
def test_mercadopago_month_name_to_number_rejects_unknown_month(summary):
    with pytest.raises(ValueError, match="Unknown month name"):
        summary.month_name_to_number("zzz")
