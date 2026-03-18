"""Statement format registry and auto-detection helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable
import unicodedata

from santander_visa_parser.credit_card_account_summary_format import (
    CreditCardAccountSummaryFormat,
)
from santander_visa_parser.galicia_mastercard_summary import GaliciaMastercardSummary
from santander_visa_parser.galicia_visa_summary import GaliciaVISASummary
from santander_visa_parser.mercadopago_account_summary import MercadoPagoAccountSummary
from santander_visa_parser.santander_rio_visa_summary import SantanderRioVISASummary


FormatFactory = Callable[[], CreditCardAccountSummaryFormat]
FormatDetector = Callable[[str, Path], bool]


@dataclass(frozen=True)
class FormatRegistration:
    """Registered statement format entry."""

    name: str
    factory: FormatFactory
    detector: FormatDetector


class StatementFormatRegistry:
    """Registry that resolves statement parser implementations."""

    def __init__(self) -> None:
        self._entries = (
            FormatRegistration(
                name="mercadopago",
                factory=MercadoPagoAccountSummary,
                detector=lambda text, path: "DETALLE DE MOVIMIENTOS" in normalize_text(text)
                and "CVU:" in text,
            ),
            FormatRegistration(
                name="galicia-mastercard",
                factory=GaliciaMastercardSummary,
                detector=lambda text, path: "MASTERCARD" in normalize_text(text)
                and "N° de Socio:" in text,
            ),
            FormatRegistration(
                name="santander-rio-visa",
                factory=SantanderRioVISASummary,
                detector=lambda text, path: "SANTANDER RIO" in normalize_text(text),
            ),
            FormatRegistration(
                name="galicia-visa",
                factory=GaliciaVISASummary,
                detector=lambda text, path: "RESUMEN N° VI" in text
                or "BANCO GALICIA" in normalize_text(text),
            ),
        )

    def names(self) -> tuple[str, ...]:
        """Return the registered format names."""
        return tuple(entry.name for entry in self._entries)

    def resolve(
        self,
        format_name: str,
        *,
        text: str,
        source_file: Path,
    ) -> tuple[str, CreditCardAccountSummaryFormat]:
        """Resolve a parser by explicit name or via auto-detection."""
        if format_name != "auto":
            for entry in self._entries:
                if entry.name == format_name:
                    return entry.name, entry.factory()
            raise ValueError(f"Unknown statement format: {format_name}")

        for entry in self._entries:
            if entry.detector(text, source_file):
                return entry.name, entry.factory()
        raise ValueError(f"Could not auto-detect statement format for {source_file.name}")


def normalize_text(value: str) -> str:
    """Return an uppercase accent-free representation suitable for detection."""
    normalized = unicodedata.normalize("NFD", value)
    normalized = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    return normalized.upper()
