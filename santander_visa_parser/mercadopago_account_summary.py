"""MercadoPago account summary concrete parsing strategy."""

from __future__ import annotations

import logging
import re
import unicodedata
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable

from santander_visa_parser.credit_card_account_summary_format import (
    CreditCardAccountSummaryFormat,
)
from santander_visa_parser.models import StatementContext, Transaction

LOGGER = logging.getLogger(__name__)


class MercadoPagoAccountSummary(CreditCardAccountSummaryFormat):
    """Concrete strategy for MercadoPago account statements."""

    MONTHS = {
        "ENERO": 1,
        "FEBRERO": 2,
        "MARZO": 3,
        "ABRIL": 4,
        "MAYO": 5,
        "JUNIO": 6,
        "JULIO": 7,
        "AGOSTO": 8,
        "SEPTIEMBRE": 9,
        "SETIEMBRE": 9,
        "OCTUBRE": 10,
        "NOVIEMBRE": 11,
        "DICIEMBRE": 12,
    }

    PERIOD_RE = re.compile(
        r"Del\s+\d{1,2}\s+al\s+(?P<day>\d{1,2})\s+de\s+(?P<month>[A-Za-zÁÉÍÓÚáéíóú]+)\s+de\s+(?P<year>\d{4})",
        re.IGNORECASE,
    )
    DATE_RE = re.compile(r"^(?P<day>\d{2})-(?P<month>\d{2})-(?P<year>\d{4})\b")
    ROW_RE = re.compile(
        r"""
        ^
        (?P<description>.+?)
        \s+(?P<reference>\d{9,})
        \s+\$\s*(?P<amount>-?[\d\.]+,\d{2})
        \s+\$\s*(?P<balance>-?[\d\.]+,\d{2})
        \s*$
        """,
        re.VERBOSE,
    )

    HEADER_PREFIXES = (
        "RESUMEN DE CUENTA",
        "CVU:",
        "CUIT/CUIL:",
        "PERIODO:",
        "SALDO INICIAL:",
        "ENTRADAS:",
        "SALIDAS:",
        "SALDO FINAL:",
        "DETALLE DE MOVIMIENTOS",
        "FECHA DESCRIPCION ID DE LA OPERACION VALOR SALDO",
        "FECHA DE GENERACION:",
        "MERCADO LIBRE S.R.L.",
    )

    def parse_statement_context(self, text: str) -> StatementContext:
        match = self.PERIOD_RE.search(text)
        if not match:
            raise ValueError("Could not determine MercadoPago statement period.")
        month = self.month_name_to_number(match.group("month"))
        return StatementContext(
            close_date=date(int(match.group("year")), month, int(match.group("day")))
        )

    def parse_transactions(
        self,
        text: str,
        source_file: Path,
        currency_filter: str | None = None,
    ) -> list[dict[str, str | int]]:
        context = self.parse_statement_context(text)
        normalized_lines = self.normalize_lines(text.splitlines())
        parsed: list[Transaction] = []
        seen_rows: set[str] = set()

        for line_no, line in normalized_lines:
            prefix_match = self.DATE_RE.match(line)
            if not prefix_match:
                continue

            body = line[prefix_match.end() :].strip()
            transaction = self.parse_transaction_body(
                body=body,
                source_file=source_file,
                line=line,
                line_no=line_no,
                day=int(prefix_match.group("day")),
                month=int(prefix_match.group("month")),
                year=int(prefix_match.group("year")),
                statement_close_date=context.close_date.isoformat(),
                reference="",
            )
            if transaction is None:
                LOGGER.debug(
                    "Skipped unparsable candidate %s in %s: %s",
                    line_no,
                    source_file.name,
                    line,
                )
                continue

            if currency_filter and transaction.currency != currency_filter:
                continue

            dedupe_key = self.collapse_whitespace(transaction.raw_line)
            if dedupe_key in seen_rows:
                continue
            seen_rows.add(dedupe_key)
            parsed.append(transaction)

        parsed.sort(key=lambda item: (item.transaction_date, item.source_line_no, item.description))
        return [item.to_row() for item in parsed]

    def normalize_lines(self, lines: Iterable[str]) -> list[tuple[int, str]]:
        normalized_lines: list[tuple[int, str]] = []
        current_parts: list[str] = []
        current_line_no = 0
        in_detail_section = False

        for line_no, raw_line in enumerate(lines, start=1):
            line = self.collapse_whitespace(raw_line)
            if not line:
                continue
            if re.match(r"^\d+/\d+$", line):
                continue
            normalized = self.normalize_text(line)
            if "DETALLE DE MOVIMIENTOS" in normalized:
                in_detail_section = True
                continue
            if not in_detail_section:
                continue
            if self.is_header_line(line):
                continue
            if self.DATE_RE.match(line):
                if current_parts:
                    normalized_lines.append((current_line_no, " ".join(current_parts)))
                current_line_no = line_no
                current_parts = [line]
                continue
            if current_parts:
                current_parts.append(line)

        if current_parts:
            normalized_lines.append((current_line_no, " ".join(current_parts)))

        return normalized_lines

    def should_merge_with_previous(
        self,
        line: str,
        merged: list[tuple[int, str]],
        previous_index: int,
    ) -> bool:
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
        match = self.ROW_RE.match(body)
        if not match:
            return None

        amount = self.parse_decimal(match.group("amount"))
        if not amount:
            return None

        return Transaction(
            source_file=source_file.name,
            statement_close_date=statement_close_date,
            transaction_date=date(year, month, day).isoformat(),
            day=day,
            month=month,
            year=year,
            description=match.group("description").strip(),
            currency="ARS",
            amount=amount,
            ars_amount=amount,
            usd_amount="",
            original_currency="",
            original_amount="",
            installment="",
            reference=match.group("reference"),
            raw_line=line,
            source_line_no=line_no,
        )

    def is_header_line(self, line: str) -> bool:
        normalized = self.normalize_text(line)
        return any(normalized.startswith(prefix) for prefix in self.HEADER_PREFIXES)

    def is_summary_line(self, line: str) -> bool:
        return False

    def month_name_to_number(self, value: str) -> int:
        key = self.normalize_text(value)
        if key not in self.MONTHS:
            raise ValueError(f"Unknown month name: {value}")
        return self.MONTHS[key]

    def parse_decimal(self, value: str) -> str:
        candidate = value.strip()
        if not candidate:
            return ""
        negative = candidate.endswith("-") or candidate.startswith("-")
        candidate = candidate.strip("-").replace(".", "").replace(",", ".")
        try:
            decimal_value = Decimal(candidate)
        except (InvalidOperation, ValueError):
            return ""
        if negative:
            decimal_value *= Decimal("-1")
        return format(decimal_value.quantize(Decimal("0.01")), "f")

    def collapse_whitespace(self, value: str) -> str:
        return re.sub(r"\s+", " ", value).strip()

    def normalize_text(self, value: str) -> str:
        normalized = unicodedata.normalize("NFD", value)
        normalized = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
        return normalized.upper()
