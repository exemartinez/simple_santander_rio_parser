"""Transaction parsing logic for Santander Visa statements."""

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import asdict, dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable

LOGGER = logging.getLogger(__name__)

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
LEGACY_STATEMENT_DATE_RE = re.compile(r"(?P<day>\d{2})-(?P<month>\d{2})-(?P<year>\d{4})")
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


def parse_statement_context(text: str) -> StatementContext:
    """Extract the statement closing date."""
    match = STATEMENT_DATE_RE.search(text)
    if match:
        day = int(match.group("day"))
        month = month_name_to_number(match.group("month"))
        year = 2000 + int(match.group("year"))
        return StatementContext(close_date=date(year, month, day))

    legacy_match = LEGACY_STATEMENT_DATE_RE.search(text)
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
    text: str,
    source_file: Path,
    currency_filter: str | None = None,
) -> list[dict[str, str | int]]:
    """Parse purchase transactions from statement text."""
    context = parse_statement_context(text)
    normalized_lines = normalize_lines(text.splitlines())
    parsed: list[Transaction] = []
    seen_rows: set[str] = set()

    current_month = context.close_date.month
    current_year = context.close_date.year

    for line_no, line in normalized_lines:
        prefix_match = TRANSACTION_PREFIX_RE.match(line)
        if not prefix_match:
            LOGGER.debug("Skipped line %s in %s: %s", line_no, source_file.name, line)
            continue

        month_name = prefix_match.group("month_name")
        if month_name:
            current_month = month_name_to_number(month_name)
            current_year = 2000 + int(prefix_match.group("year"))

        body = prefix_match.group("body")
        if is_summary_line(body) or is_header_line(body):
            LOGGER.debug("Skipped non-transaction line %s in %s: %s", line_no, source_file.name, line)
            continue

        transaction = parse_transaction_body(
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
            LOGGER.debug("Skipped unparsable candidate %s in %s: %s", line_no, source_file.name, line)
            continue

        if currency_filter and transaction.currency != currency_filter:
            continue

        dedupe_key = collapse_whitespace(transaction.raw_line)
        if dedupe_key in seen_rows:
            LOGGER.debug("Skipped duplicate line %s in %s: %s", line_no, source_file.name, line)
            continue

        seen_rows.add(dedupe_key)
        parsed.append(transaction)

    parsed.sort(key=lambda item: (item.transaction_date, item.source_line_no, item.description))
    return [item.to_row() for item in parsed]


def normalize_lines(lines: Iterable[str]) -> list[tuple[int, str]]:
    """Normalize and merge multiline text fragments from the PDF extraction."""
    merged: list[tuple[int, str]] = []
    previous_index = -1

    for line_no, raw_line in enumerate(lines, start=1):
        line = collapse_whitespace(raw_line)
        if not line:
            continue
        if set(line) == {"_"}:
            continue
        if should_merge_with_previous(line, merged, previous_index):
            base_line_no, base_text = merged[previous_index]
            merged[previous_index] = (base_line_no, f"{base_text} {line}".strip())
            continue

        merged.append((line_no, line))
        previous_index = len(merged) - 1

    return merged


def should_merge_with_previous(
    line: str,
    merged: list[tuple[int, str]],
    previous_index: int,
) -> bool:
    """Return whether a line is likely a continuation of the previous transaction description."""
    if previous_index < 0:
        return False
    if is_header_line(line) or is_summary_line(line):
        return False
    if re.match(r"^\d{2}\s+[A-Za-zÁÉÍÓÚÜÑáéíóúüñ\.]+\s+\d{2}\b", line):
        return False
    if re.match(r"^\d{2}\s+\d{6}\b", line):
        return False
    if re.match(r"^\d{2}\b", line):
        return False
    previous_line = merged[previous_index][1]
    if not TRANSACTION_PREFIX_RE.match(previous_line):
        return False
    if line.endswith(("-", ",00", ",01", ",02", ",03", ",04", ",05", ",06", ",07", ",08", ",09")):
        return False
    return True


def parse_transaction_body(
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
    """Parse the body of a normalized transaction line."""
    foreign_match = FOREIGN_BODY_RE.match(body)
    if foreign_match:
        description = foreign_match.group("description").strip()
        billed_amount = parse_decimal(foreign_match.group("billed_amount"))
        original_amount = parse_decimal(foreign_match.group("original_amount"))
        original_currency = normalize_currency(foreign_match.group("original_currency"))
        currency = "USD"
        amount = billed_amount
        ars_amount = ""
        usd_amount = billed_amount
        installment = ""
    else:
        ars_match = ARS_BODY_RE.match(body)
        if not ars_match:
            return None
        description = ars_match.group("description").strip()
        billed_amount = parse_decimal(ars_match.group("billed_amount"))
        original_amount = ""
        original_currency = ""
        currency = "ARS"
        amount = billed_amount
        ars_amount = billed_amount
        usd_amount = ""
        installment = ars_match.group("installment") or ""

    if billed_amount == "":
        return None
    if is_summary_line(description) or is_header_line(description):
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


def is_header_line(line: str) -> bool:
    """Return whether a line belongs to the repeated PDF header/footer."""
    normalized = normalize_text(line)
    return any(normalized.startswith(prefix) for prefix in HEADER_PREFIXES)


def is_summary_line(line: str) -> bool:
    """Return whether a line belongs to balances, totals, taxes, or explanatory sections."""
    normalized = normalize_text(line)
    return any(keyword in normalized for keyword in SUMMARY_KEYWORDS)


def normalize_currency(value: str) -> str:
    """Normalize statement currency labels."""
    value = value.strip().upper()
    if value == "U$S":
        return "USD"
    return value


def parse_decimal(value: str) -> str:
    """Convert a statement amount to a normalized decimal string."""
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


def month_name_to_number(value: str) -> int:
    """Map a Spanish month label to a month number."""
    key = normalize_text(value).replace(".", "").lower()
    if key not in SPANISH_MONTHS:
        raise ValueError(f"Unknown month name: {value}")
    return SPANISH_MONTHS[key]


def collapse_whitespace(value: str) -> str:
    """Collapse repeated spaces while preserving readable line structure."""
    return re.sub(r"\s+", " ", value).strip()


def normalize_text(value: str) -> str:
    """Normalize text for resilient keyword checks."""
    normalized = unicodedata.normalize("NFD", value)
    normalized = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    return normalized.upper()
