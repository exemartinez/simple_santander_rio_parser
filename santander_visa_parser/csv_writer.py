"""Object-oriented CSV output helpers for Santander Visa transactions."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

class TransactionCSVWriter:
    """Write normalized transactions to CSV."""

    FIELDNAMES = [
        "source_file",
        "statement_close_date",
        "transaction_date",
        "day",
        "month",
        "year",
        "description",
        "currency",
        "amount",
        "ars_amount",
        "usd_amount",
        "original_currency",
        "original_amount",
        "installment",
        "reference",
        "source_line_no",
        "raw_line",
    ]

    def write(
        self,
        rows: Iterable[dict[str, object]],
        output_path: Path,
        use_pandas: bool = False,
    ) -> None:
        """Write normalized transactions to CSV."""
        prepared_rows = list(rows)
        if use_pandas:
            try:
                import pandas as pd
            except ImportError as exc:
                raise RuntimeError(
                    "pandas is not installed. Install it or run without --use-pandas."
                ) from exc

            frame = pd.DataFrame(prepared_rows, columns=self.FIELDNAMES)
            frame.to_csv(output_path, index=False)
            return

        with output_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=self.FIELDNAMES)
            writer.writeheader()
            writer.writerows(prepared_rows)
