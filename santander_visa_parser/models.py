"""Shared parser domain models."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date


@dataclass(frozen=True)
class StatementContext:
    """Metadata extracted from a statement."""

    close_date: date


@dataclass(frozen=True)
class Transaction:
    """Normalized transaction extracted from a statement."""

    source_file: str
    statement_close_date: str
    transaction_date: str
    day: int
    month: int
    year: int
    description: str
    currency: str
    amount: str
    ars_amount: str
    usd_amount: str
    original_currency: str
    original_amount: str
    installment: str
    reference: str
    raw_line: str
    source_line_no: int

    def to_row(self) -> dict[str, str | int]:
        """Return a dict representation suitable for CSV writing."""
        return asdict(self)

