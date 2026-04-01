from __future__ import annotations

from pathlib import Path

from santander_visa_parser.transaction_parser import TransactionParser


# Purpose: verify TransactionParser delegates directly to the configured strategy.
def test_transaction_parser_delegates_to_summary_format(dummy_format):
    parser = TransactionParser(dummy_format)

    rows = parser.parse("purchase", Path("statement.pdf"), currency_filter="ARS")

    assert rows == [
        {
            "source_file": "statement.pdf",
            "statement_close_date": "2026-01-08",
            "transaction_date": "2026-01-08",
            "day": 8,
            "month": 1,
            "year": 2026,
            "description": "purchase",
            "currency": "ARS",
            "amount": "10.00",
            "ars_amount": "10.00",
            "usd_amount": "",
            "original_currency": "",
            "original_amount": "",
            "installment": "",
            "reference": "ref",
            "raw_line": "purchase",
            "source_line_no": 1,
        }
    ]
