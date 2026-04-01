from __future__ import annotations

from santander_visa_parser.models import StatementContext, Transaction


# Purpose: verify Transaction.to_row preserves the normalized schema as a plain dict.
def test_transaction_to_row_returns_all_fields():
    transaction = Transaction(
        source_file="statement.pdf",
        statement_close_date="2026-01-08",
        transaction_date="2025-12-20",
        day=20,
        month=12,
        year=2025,
        description="MERPAGO*WOK",
        currency="ARS",
        amount="1421.34",
        ars_amount="1421.34",
        usd_amount="",
        original_currency="",
        original_amount="",
        installment="C.05/18",
        reference="966693",
        raw_line="25 Diciem. 20 966693 * MERPAGO*WOK C.05/18 1.421,34",
        source_line_no=33,
    )

    assert transaction.to_row() == {
        "source_file": "statement.pdf",
        "statement_close_date": "2026-01-08",
        "transaction_date": "2025-12-20",
        "day": 20,
        "month": 12,
        "year": 2025,
        "description": "MERPAGO*WOK",
        "currency": "ARS",
        "amount": "1421.34",
        "ars_amount": "1421.34",
        "usd_amount": "",
        "original_currency": "",
        "original_amount": "",
        "installment": "C.05/18",
        "reference": "966693",
        "raw_line": "25 Diciem. 20 966693 * MERPAGO*WOK C.05/18 1.421,34",
        "source_line_no": 33,
    }


# Purpose: verify the statement context dataclass stores the extracted close date cleanly.
def test_statement_context_exposes_close_date():
    context = StatementContext(close_date=__import__("datetime").date(2026, 1, 8))

    assert context.close_date.isoformat() == "2026-01-08"
