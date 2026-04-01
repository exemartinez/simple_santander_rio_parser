from __future__ import annotations

from abc import abstractmethod
from pathlib import Path

import pytest

from santander_visa_parser.credit_card_account_summary_format import (
    CreditCardAccountSummaryFormat,
)
from santander_visa_parser.models import StatementContext


# Purpose: verify the strategy interface keeps its abstract contract in place.
def test_credit_card_account_summary_format_cannot_be_instantiated_directly():
    with pytest.raises(TypeError):
        CreditCardAccountSummaryFormat()


# Purpose: verify all expected abstract methods stay declared on the interface.
def test_credit_card_account_summary_format_exposes_expected_abstract_methods():
    expected = {
        "parse_statement_context",
        "parse_transactions",
        "normalize_lines",
        "should_merge_with_previous",
        "parse_transaction_body",
        "is_header_line",
        "is_summary_line",
    }
    assert CreditCardAccountSummaryFormat.__abstractmethods__ == expected


# Purpose: verify a concrete implementation satisfies the interface end to end.
def test_credit_card_account_summary_format_concrete_subclass_can_be_used(dummy_format):
    assert dummy_format.parse_statement_context("anything") == StatementContext(
        close_date=__import__("datetime").date(2026, 1, 8)
    )
    assert dummy_format.parse_transactions("purchase", Path("statement.pdf"))[0]["description"] == "purchase"
    assert dummy_format.normalize_lines(["a", "b"]) == [(1, "a"), (2, "b")]
    assert dummy_format.should_merge_with_previous("line", [], -1) is False
    assert dummy_format.is_header_line("header row") is True
    assert dummy_format.is_summary_line("summary row") is True


# Purpose: verify Python still prevents partially implemented subclasses from being instantiated.
def test_credit_card_account_summary_format_rejects_incomplete_subclass():
    class IncompleteFormat(CreditCardAccountSummaryFormat):
        @abstractmethod
        def parse_statement_context(self, text: str):
            raise NotImplementedError

    with pytest.raises(TypeError):
        IncompleteFormat()
