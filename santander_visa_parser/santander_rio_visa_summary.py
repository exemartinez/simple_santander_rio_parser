"""Santander Rio VISA concrete parsing strategy."""

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


class SantanderRioVISASummary(CreditCardAccountSummaryFormat):
    """Concrete strategy for Santander Rio VISA statements."""

    SPANISH_MONTHS = {
        "ene": 1,
        "enero": 1,
        "feb": 2,
        "febrero": 2,
        "mar": 3,
        "marzo": 3,
        "abr": 4,
        "abril": 4,
        "may": 5,
        "mayo": 5,
        "jun": 6,
        "junio": 6,
        "jul": 7,
        "julio": 7,
        "ago": 8,
        "agosto": 8,
        "set": 9,
        "setiembre": 9,
        "sep": 9,
        "sept": 9,
        "septiembre": 9,
        "oct": 10,
        "octubre": 10,
        "nov": 11,
        "noviembre": 11,
        "dic": 12,
        "diciem": 12,
        "diciembre": 12,
    }

    HEADER_PREFIXES = (
        "SANTANDER RIO",
        "RESUMEN DE CUENTA",
        "VISA",
        "SUCURSAL:",
        "GRUPO:",
        "CUENTA:",
        "FECHA COMPROBANTE REFERENCIA",
        "EL PRESENTE ES COPIA DEL ORIGINAL",
        "SALDO ACTUAL",
        "PAGO MINIMO",
        "CASA CENTRAL",
        "SUPERCLUB PAQUETE",
        "IVA:",
        "MARTINEZ,",
        "GRAL GUILLERMO",
        "CAP.FEDERAL",
        "CIERRE ANT.:",
        "PROX.CIERRE:",
        "LIMITES:",
        "LE RECORDAMOS",
        "(PIN).",
        "NO TIENE CLAVE",
    )

    SUMMARY_KEYWORDS = (
        "SALDO ANTERIOR",
        "SU PAGO EN",
        "TRANSFERENCIA DEUDA",
        "TOTAL CONSUMOS",
        "INTERESES FINANCIACION",
        "DB IVA",
        "IIBB PERCEP",
        "IVA RG",
        "DB.RG 5617",
        "DB RG 5617",
        "PLAN V",
        "CUOTAS A VENCER",
        "CONDICIONES VIGENTES",
        "NO RENOVACION",
        "NO RENOVACIÓN",
        "RESPONDIENDO A LA RG",
    )

    STATEMENT_DATE_RE = re.compile(
        r"CIERRE\s+(?P<day>\d{2})\s+(?P<month>[A-Za-zÁÉÍÓÚÜÑáéíóúüñ\.]+)\s+(?P<year>\d{2})",
        re.IGNORECASE,
    )
    LEGACY_STATEMENT_DATE_RE = re.compile(
        r"(?P<day>\d{2})-(?P<month>\d{2})-(?P<year>\d{4})"
    )
    TRANSACTION_PREFIX_RE = re.compile(
        r"""
        ^\s*
        (?:(?P<year>\d{2})\s+(?P<month_name>[A-Za-zÁÉÍÓÚÜÑáéíóúüñ\.]+)\s+)?
        (?P<day>\d{2})
        \s+
        (?:(?P<reference>\d{6})\s+)?
        (?:(?P<marker>[A-Z\*])\s+)?
        (?P<body>\S.*?)
        \s*$
        """,
        re.VERBOSE,
    )
    FOREIGN_BODY_RE = re.compile(
        r"""
        ^
        (?P<description>.+?)
        (?:\s+)?
        (?P<original_currency>USD|U\$S|EUR)
        \s+
        (?P<original_amount>-?[\d\.,]+)
        \s+
        (?P<billed_amount>-?[\d\.,]+-?)
        $
        """,
        re.VERBOSE,
    )
    ARS_BODY_RE = re.compile(
        r"""
        ^
        (?P<description>.+?)
        (?:
            \s+
            (?P<installment>C\.\d{2}/\d{2})
        )?
        \s+
        (?P<billed_amount>-?[\d\.,]+-?)
        $
        """,
        re.VERBOSE,
    )

    def parse_statement_context(self, text: str) -> StatementContext:
        match = self.STATEMENT_DATE_RE.search(text)
        if match:
            day = int(match.group("day"))
            month = self.month_name_to_number(match.group("month"))
            year = 2000 + int(match.group("year"))
            return StatementContext(close_date=date(year, month, day))

        legacy_match = self.LEGACY_STATEMENT_DATE_RE.search(text)
        if legacy_match:
            return StatementContext(
                close_date=date(
                    int(legacy_match.group("year")),
                    int(legacy_match.group("month")),
                    int(legacy_match.group("day")),
                )
            )

        raise ValueError("Could not determine statement closing date.")

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

        current_month = context.close_date.month
        current_year = context.close_date.year

        for line_no, line in normalized_lines:
            prefix_match = self.TRANSACTION_PREFIX_RE.match(line)
            if not prefix_match:
                LOGGER.debug("Skipped line %s in %s: %s", line_no, source_file.name, line)
                continue

            month_name = prefix_match.group("month_name")
            if month_name:
                current_month = self.month_name_to_number(month_name)
                current_year = 2000 + int(prefix_match.group("year"))

            body = prefix_match.group("body")
            if self.is_summary_line(body) or self.is_header_line(body):
                LOGGER.debug(
                    "Skipped non-transaction line %s in %s: %s",
                    line_no,
                    source_file.name,
                    line,
                )
                continue

            transaction = self.parse_transaction_body(
                body=body,
                source_file=source_file,
                line=line,
                line_no=line_no,
                day=int(prefix_match.group("day")),
                month=current_month,
                year=current_year,
                statement_close_date=context.close_date.isoformat(),
                reference=prefix_match.group("reference") or "",
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
                LOGGER.debug("Skipped duplicate line %s in %s: %s", line_no, source_file.name, line)
                continue

            seen_rows.add(dedupe_key)
            parsed.append(transaction)

        parsed.sort(key=lambda item: (item.transaction_date, item.source_line_no, item.description))
        return [item.to_row() for item in parsed]

    def normalize_lines(self, lines: Iterable[str]) -> list[tuple[int, str]]:
        merged: list[tuple[int, str]] = []
        previous_index = -1

        for line_no, raw_line in enumerate(lines, start=1):
            line = self.collapse_whitespace(raw_line)
            if not line:
                continue
            if set(line) == {"_"}:
                continue
            if self.should_merge_with_previous(line, merged, previous_index):
                base_line_no, base_text = merged[previous_index]
                merged[previous_index] = (base_line_no, f"{base_text} {line}".strip())
                continue

            merged.append((line_no, line))
            previous_index = len(merged) - 1

        return merged

    def should_merge_with_previous(
        self,
        line: str,
        merged: list[tuple[int, str]],
        previous_index: int,
    ) -> bool:
        if previous_index < 0:
            return False
        if self.is_header_line(line) or self.is_summary_line(line):
            return False
        if re.match(r"^\d{2}\s+[A-Za-zÁÉÍÓÚÜÑáéíóúüñ\.]+\s+\d{2}\b", line):
            return False
        if re.match(r"^\d{2}\s+\d{6}\b", line):
            return False
        if re.match(r"^\d{2}\b", line):
            return False
        previous_line = merged[previous_index][1]
        if not self.TRANSACTION_PREFIX_RE.match(previous_line):
            return False
        if line.endswith(("-", ",00", ",01", ",02", ",03", ",04", ",05", ",06", ",07", ",08", ",09")):
            return False
        return True

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
        foreign_match = self.FOREIGN_BODY_RE.match(body)
        if foreign_match:
            description = foreign_match.group("description").strip()
            billed_amount = self.parse_decimal(foreign_match.group("billed_amount"))
            original_amount = self.parse_decimal(foreign_match.group("original_amount"))
            original_currency = self.normalize_currency(foreign_match.group("original_currency"))
            currency = "USD"
            amount = billed_amount
            ars_amount = ""
            usd_amount = billed_amount
            installment = ""
        else:
            ars_match = self.ARS_BODY_RE.match(body)
            if not ars_match:
                return None
            description = ars_match.group("description").strip()
            billed_amount = self.parse_decimal(ars_match.group("billed_amount"))
            original_amount = ""
            original_currency = ""
            currency = "ARS"
            amount = billed_amount
            ars_amount = billed_amount
            usd_amount = ""
            installment = ars_match.group("installment") or ""

        if billed_amount == "":
            return None
        if self.is_summary_line(description) or self.is_header_line(description):
            return None

        transaction_date = date(year, month, day).isoformat()
        return Transaction(
            source_file=source_file.name,
            statement_close_date=statement_close_date,
            transaction_date=transaction_date,
            day=day,
            month=month,
            year=year,
            description=description,
            currency=currency,
            amount=amount,
            ars_amount=ars_amount,
            usd_amount=usd_amount,
            original_currency=original_currency,
            original_amount=original_amount,
            installment=installment,
            reference=reference,
            raw_line=line,
            source_line_no=line_no,
        )

    def is_header_line(self, line: str) -> bool:
        normalized = self.normalize_text(line)
        return any(normalized.startswith(prefix) for prefix in self.HEADER_PREFIXES)

    def is_summary_line(self, line: str) -> bool:
        normalized = self.normalize_text(line)
        return any(keyword in normalized for keyword in self.SUMMARY_KEYWORDS)

    def normalize_currency(self, value: str) -> str:
        normalized = value.strip().upper()
        if normalized == "U$S":
            return "USD"
        return normalized

    def parse_decimal(self, value: str) -> str:
        candidate = value.strip()
        negative = candidate.endswith("-") or candidate.startswith("-")
        candidate = candidate.strip("-").replace(".", "").replace(",", ".")
        try:
            decimal_value = Decimal(candidate)
        except (InvalidOperation, ValueError):
            return ""
        if negative:
            decimal_value *= Decimal("-1")
        return format(decimal_value.quantize(Decimal("0.01")), "f")

    def month_name_to_number(self, value: str) -> int:
        key = self.normalize_text(value).replace(".", "").lower()
        if key not in self.SPANISH_MONTHS:
            raise ValueError(f"Unknown month name: {value}")
        return self.SPANISH_MONTHS[key]

    def collapse_whitespace(self, value: str) -> str:
        return re.sub(r"\s+", " ", value).strip()

    def normalize_text(self, value: str) -> str:
        normalized = unicodedata.normalize("NFD", value)
        normalized = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
        return normalized.upper()

