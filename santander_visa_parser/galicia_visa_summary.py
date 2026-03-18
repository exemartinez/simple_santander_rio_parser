"""Banco Galicia VISA concrete parsing strategy."""

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


class GaliciaVISASummary(CreditCardAccountSummaryFormat):
    """Concrete strategy for Banco Galicia VISA statements."""

    MONTHS = {
        "ENE": 1,
        "FEB": 2,
        "MAR": 3,
        "ABR": 4,
        "MAY": 5,
        "JUN": 6,
        "JUL": 7,
        "AGO": 8,
        "SEP": 9,
        "SET": 9,
        "OCT": 10,
        "NOV": 11,
        "DIC": 12,
    }

    DATE_RE = re.compile(r"^(?P<day>\d{2})-(?P<month>\d{2}|[A-Za-z]{3})-(?P<year>\d{2})\b")
    BARCODE_DATE_RE = re.compile(r"\b(?P<close_date>20\d{6})\d+H\b")
    TRAILING_AMOUNTS_RE = re.compile(
        r"""
        ^
        (?P<core>.+?)
        \s+
        (?P<amount_1>-?[\d\.]+,\d{2})
        (?:\s+(?P<amount_2>-?[\d\.]+,\d{2}))?
        \s*$
        """,
        re.VERBOSE,
    )
    HEADER_PREFIXES = (
        "RESUMEN N°",
        "TARJETA CREDITO",
        "RESUMEN DE TARJETA DE CREDITO",
        "PAGINA ",
        "PAGO MINIMO",
        "LIMITES",
        "TASAS",
        "CONSOLIDADO",
        "DETALLE DEL CONSUMO",
        "FECHA REFERENCIA CUOTA COMPROBANTE PESOS DOLARES",
    )

    SUMMARY_KEYWORDS = (
        "SALDO ANTERIOR",
        "SU PAGO EN PESOS",
        "TRANSFERENCIA DEUDA",
        "TOTAL CONSUMOS",
        "INTERESES FINANCIACION",
        "DB IVA",
        "TOTAL A PAGAR",
        "PLAN V",
        "CUOTAS A VENCER",
        "CONDICIONES VIGENTES",
        "TARJETA ",
        "SUBTOTAL",
    )

    def parse_statement_context(self, text: str) -> StatementContext:
        match = self.BARCODE_DATE_RE.search(text)
        if not match:
            raise ValueError("Could not determine Galicia VISA statement closing date.")
        close_date = datetime_from_yyyymmdd(match.group("close_date"))
        return StatementContext(close_date=close_date)

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
        in_detail_section = False

        for line_no, line in normalized_lines:
            normalized = self.normalize_text(line)
            if "DETALLE DEL CONSUMO" in normalized:
                in_detail_section = True
                continue
            if not in_detail_section:
                continue

            prefix_match = self.DATE_RE.match(line)
            if not prefix_match:
                LOGGER.debug("Skipped line %s in %s: %s", line_no, source_file.name, line)
                continue

            body = line[prefix_match.end() :].strip()
            if self.is_header_line(body) or self.is_summary_line(body):
                continue

            transaction = self.parse_transaction_body(
                body=body,
                source_file=source_file,
                line=line,
                line_no=line_no,
                day=int(prefix_match.group("day")),
                month=self.month_name_to_number(prefix_match.group("month")),
                year=2000 + int(prefix_match.group("year")),
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
        for line_no, raw_line in enumerate(lines, start=1):
            line = self.collapse_whitespace(raw_line)
            if not line:
                continue
            normalized_lines.append((line_no, line))
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
        markerless_body = re.sub(r"^(?:\*|K)\s+", "", body).strip()
        amounts_match = self.TRAILING_AMOUNTS_RE.match(markerless_body)
        if not amounts_match:
            return None

        core = amounts_match.group("core").strip()
        amount_1 = self.parse_decimal(amounts_match.group("amount_1"))
        amount_2 = self.parse_decimal(amounts_match.group("amount_2") or "")
        if not amount_1:
            return None

        description, installment, reference = self.split_core(core)

        if self.is_summary_line(description) or self.is_header_line(description):
            return None

        currency = "USD" if amount_2 else "ARS"
        amount = amount_2 if amount_2 else amount_1
        ars_amount = amount_1 if currency == "ARS" else ""
        usd_amount = amount_2 if amount_2 else ""

        return Transaction(
            source_file=source_file.name,
            statement_close_date=statement_close_date,
            transaction_date=date(year, month, day).isoformat(),
            day=day,
            month=month,
            year=year,
            description=description,
            currency=currency,
            amount=amount,
            ars_amount=ars_amount,
            usd_amount=usd_amount,
            original_currency="",
            original_amount="",
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

    def month_name_to_number(self, value: str) -> int:
        if value.isdigit():
            return int(value)
        key = self.normalize_text(value).replace(".", "")[:3]
        if key not in self.MONTHS:
            raise ValueError(f"Unknown month name: {value}")
        return self.MONTHS[key]

    def split_core(self, core: str) -> tuple[str, str, str]:
        installment_match = re.search(r"\s(?P<installment>\d{2}/\d{2})\s", core)
        installment = ""
        if installment_match:
            installment = installment_match.group("installment")
            core = re.sub(rf"\s{re.escape(installment)}\s", " ", core, count=1).strip()

        two_part_reference = re.match(r"^(?P<description>.+?)\s+(?P<reference>\d{10,}\s+\d{6})$", core)
        if two_part_reference:
            return (
                two_part_reference.group("description").strip(),
                installment,
                two_part_reference.group("reference").strip(),
            )

        single_reference = re.match(r"^(?P<description>.+?)\s+(?P<reference>\d{5,})$", core)
        if single_reference:
            return (
                single_reference.group("description").strip(),
                installment,
                single_reference.group("reference").strip(),
            )

        return core, installment, ""

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


def datetime_from_yyyymmdd(value: str) -> date:
    """Return a date parsed from YYYYMMDD."""
    return date(int(value[0:4]), int(value[4:6]), int(value[6:8]))
