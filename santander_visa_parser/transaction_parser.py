"""Strategy context for statement transaction parsing."""

from __future__ import annotations

from pathlib import Path

from santander_visa_parser.credit_card_account_summary_format import (
    CreditCardAccountSummaryFormat,
)


class TransactionParser:
    """Strategy context for statement transaction parsing."""

    def __init__(self, summary_format: CreditCardAccountSummaryFormat) -> None:
        self.summary_format = summary_format

    def parse(
        self,
        text: str,
        source_file: Path,
        currency_filter: str | None = None,
    ) -> list[dict[str, str | int]]:
        """Delegate parsing to the configured summary format."""
        return self.summary_format.parse_transactions(text, source_file, currency_filter)
