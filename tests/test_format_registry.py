from __future__ import annotations

from pathlib import Path

import pytest

from santander_visa_parser.format_registry import StatementFormatRegistry, normalize_text
from santander_visa_parser.galicia_mastercard_summary import GaliciaMastercardSummary
from santander_visa_parser.galicia_visa_summary import GaliciaVISASummary
from santander_visa_parser.mercadopago_account_summary import MercadoPagoAccountSummary
from santander_visa_parser.santander_rio_visa_summary import SantanderRioVISASummary


# Purpose: verify the registry advertises the supported formats in CLI order.
def test_format_registry_names_returns_registered_formats():
    registry = StatementFormatRegistry()

    assert registry.names() == (
        "mercadopago",
        "galicia-mastercard",
        "santander-rio-visa",
        "galicia-visa",
    )


# Purpose: verify explicit resolution returns the requested parser implementation.
@pytest.mark.parametrize(
    ("format_name", "expected_type"),
    [
        ("mercadopago", MercadoPagoAccountSummary),
        ("galicia-mastercard", GaliciaMastercardSummary),
        ("santander-rio-visa", SantanderRioVISASummary),
        ("galicia-visa", GaliciaVISASummary),
    ],
)
def test_format_registry_resolves_explicit_formats(format_name, expected_type):
    registry = StatementFormatRegistry()

    resolved_name, parser = registry.resolve(
        format_name,
        text="unused",
        source_file=Path("statement.pdf"),
    )

    assert resolved_name == format_name
    assert isinstance(parser, expected_type)


# Purpose: verify an unknown explicit format fails fast with a useful error.
def test_format_registry_rejects_unknown_explicit_format():
    registry = StatementFormatRegistry()

    with pytest.raises(ValueError, match="Unknown statement format"):
        registry.resolve("unknown", text="unused", source_file=Path("statement.pdf"))


# Purpose: verify auto detection chooses the correct parser from statement text signatures.
@pytest.mark.parametrize(
    ("text", "expected_name", "expected_type"),
    [
        ("DETALLE DE MOVIMIENTOS\nCVU: 123", "mercadopago", MercadoPagoAccountSummary),
        ("MASTERCARD\nN° de Socio: 123", "galicia-mastercard", GaliciaMastercardSummary),
        ("Santander Río\nSANTANDER RIO", "santander-rio-visa", SantanderRioVISASummary),
        ("BANCO GALICIA", "galicia-visa", GaliciaVISASummary),
    ],
)
def test_format_registry_auto_detects_supported_formats(text, expected_name, expected_type):
    registry = StatementFormatRegistry()

    resolved_name, parser = registry.resolve("auto", text=text, source_file=Path("statement.pdf"))

    assert resolved_name == expected_name
    assert isinstance(parser, expected_type)


# Purpose: verify auto detection fails clearly for unsupported statement text.
def test_format_registry_auto_detect_raises_when_no_format_matches():
    registry = StatementFormatRegistry()

    with pytest.raises(ValueError, match="Could not auto-detect statement format"):
        registry.resolve("auto", text="plain text", source_file=Path("statement.pdf"))


# Purpose: verify helper normalization removes accents and uppercases for detector reuse.
def test_format_registry_normalize_text_removes_accents_and_uppercases():
    assert normalize_text("Santander Río crédito") == "SANTANDER RIO CREDITO"
