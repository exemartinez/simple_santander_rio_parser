"""Strategy interface for credit card account summary parsers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterable

from santander_visa_parser.models import StatementContext, Transaction


class CreditCardAccountSummaryFormat(ABC):
    """Strategy interface for credit card account summary parsers."""

    @abstractmethod
    def parse_statement_context(self, text: str) -> StatementContext:
        """Extract the statement-level metadata."""

    @abstractmethod
    def parse_transactions(
        self,
        text: str,
        source_file: Path,
        currency_filter: str | None = None,
    ) -> list[dict[str, str | int]]:
        """Parse normalized transaction rows from a statement."""

    @abstractmethod
    def normalize_lines(self, lines: Iterable[str]) -> list[tuple[int, str]]:
        """Normalize and merge raw PDF text lines."""

    @abstractmethod
    def should_merge_with_previous(
        self,
        line: str,
        merged: list[tuple[int, str]],
        previous_index: int,
    ) -> bool:
        """Return whether a line should be merged with the previous one."""

    @abstractmethod
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
        """Parse a normalized transaction body into a transaction object."""

    @abstractmethod
    def is_header_line(self, line: str) -> bool:
        """Return whether a line belongs to a header or footer."""

    @abstractmethod
    def is_summary_line(self, line: str) -> bool:
        """Return whether a line belongs to summary or tax sections."""

