from __future__ import annotations

import builtins
from pathlib import Path

import pytest

from santander_visa_parser.csv_writer import TransactionCSVWriter


def sample_rows() -> list[dict[str, object]]:
    return [
        {
            "source_file": "statement.pdf",
            "statement_close_date": "2026-01-08",
            "transaction_date": "2025-12-20",
            "day": 20,
            "month": 12,
            "year": 2025,
            "description": "MERPAGO*WOK",
            "currency": "ARS",
            "amount": "1421.34",
            "ars_amount": "1421.34",
            "usd_amount": "",
            "original_currency": "",
            "original_amount": "",
            "installment": "C.05/18",
            "reference": "966693",
            "source_line_no": 33,
            "raw_line": "raw line",
        }
    ]


# Purpose: verify the standard writer emits a CSV with the declared schema and row values.
def test_csv_writer_writes_rows_without_pandas(tmp_path):
    output_path = tmp_path / "rows.csv"

    TransactionCSVWriter().write(sample_rows(), output_path)

    content = output_path.read_text(encoding="utf-8")
    assert "source_file,statement_close_date,transaction_date" in content
    assert "statement.pdf,2026-01-08,2025-12-20" in content


# Purpose: verify the pandas code path uses the expected columns and output file.
def test_csv_writer_uses_pandas_when_requested(monkeypatch, tmp_path):
    output_path = tmp_path / "rows.csv"
    calls: dict[str, object] = {}

    class FakeFrame:
        def __init__(self, rows, columns) -> None:
            calls["rows"] = rows
            calls["columns"] = columns

        def to_csv(self, path: Path, index: bool = False) -> None:
            calls["path"] = path
            calls["index"] = index

    class FakePandas:
        DataFrame = FakeFrame

    fake_import = builtins.__import__

    def import_with_fake_pandas(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "pandas":
            return FakePandas()
        return fake_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", import_with_fake_pandas)

    TransactionCSVWriter().write(sample_rows(), output_path, use_pandas=True)

    assert calls["rows"] == sample_rows()
    assert calls["columns"] == TransactionCSVWriter.FIELDNAMES
    assert calls["path"] == output_path
    assert calls["index"] is False


# Purpose: verify the pandas branch raises a clear unit-level error when pandas is unavailable.
def test_csv_writer_raises_clear_error_when_pandas_is_missing(monkeypatch, tmp_path):
    output_path = tmp_path / "rows.csv"
    real_import = builtins.__import__

    def import_without_pandas(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "pandas":
            raise ImportError("missing pandas")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", import_without_pandas)

    with pytest.raises(RuntimeError, match="pandas is not installed"):
        TransactionCSVWriter().write(sample_rows(), output_path, use_pandas=True)
