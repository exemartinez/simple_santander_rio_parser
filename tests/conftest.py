from __future__ import annotations

from pathlib import Path

import pytest

from santander_visa_parser.credit_card_account_summary_format import (
    CreditCardAccountSummaryFormat,
)
from santander_visa_parser.models import StatementContext, Transaction


class DummySummaryFormat(CreditCardAccountSummaryFormat):
    def parse_statement_context(self, text: str) -> StatementContext:
        return StatementContext(close_date=__import__("datetime").date(2026, 1, 8))

    def parse_transactions(
        self,
        text: str,
        source_file: Path,
        currency_filter: str | None = None,
    ) -> list[dict[str, str | int]]:
        row = self.parse_transaction_body(
            body=text,
            source_file=source_file,
            line=text,
            line_no=1,
            day=8,
            month=1,
            year=2026,
            statement_close_date="2026-01-08",
            reference="ref",
        )
        return [row.to_row()] if row else []

    def normalize_lines(self, lines):
        return [(index, line) for index, line in enumerate(lines, start=1)]

    def should_merge_with_previous(self, line, merged, previous_index) -> bool:
        return False

    def parse_transaction_body(
        self,
        *,
        body: str,
        source_file: Path,
        line: str,
        line_no: int,
        day: int,
        month: int,
        year: int,
        statement_close_date: str,
        reference: str,
    ) -> Transaction | None:
        if body == "skip":
            return None
        return Transaction(
            source_file=source_file.name,
            statement_close_date=statement_close_date,
            transaction_date="2026-01-08",
            day=day,
            month=month,
            year=year,
            description=body,
            currency="ARS",
            amount="10.00",
            ars_amount="10.00",
            usd_amount="",
            original_currency="",
            original_amount="",
            installment="",
            reference=reference,
            raw_line=line,
            source_line_no=line_no,
        )

    def is_header_line(self, line: str) -> bool:
        return line.startswith("header")

    def is_summary_line(self, line: str) -> bool:
        return line.startswith("summary")


@pytest.fixture
def dummy_format() -> DummySummaryFormat:
    # Purpose: share one fully concrete summary format for interface and delegation tests.
    return DummySummaryFormat()
