"""CLI entrypoint for Santander Visa PDF transaction extraction."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from santander_visa_parser.csv_writer import write_transactions_csv
from santander_visa_parser.pdf_reader import extract_text_from_pdf
from santander_visa_parser.transaction_parser import parse_transactions


def parse_args() -> argparse.Namespace:
    """Build and parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Extract Santander Visa transactions from PDF statements into CSV."
    )
    parser.add_argument("inputs", nargs="+", help="PDF files and/or folders containing PDFs.")
    parser.add_argument(
        "-o",
        "--output",
        default="output/movimientos.csv",
        help="Output CSV path.",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging for skipped lines.")
    parser.add_argument(
        "--use-pandas",
        action="store_true",
        help="Use pandas to build the CSV output when pandas is available.",
    )
    parser.add_argument(
        "--currency-filter",
        choices=("ARS", "USD"),
        help="Keep only transactions billed in the selected currency.",
    )
    return parser.parse_args()


def configure_logging(debug: bool) -> None:
    """Configure application logging."""
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(levelname)s %(message)s",
    )


def expand_input_paths(inputs: list[str]) -> list[Path]:
    """Expand input files and folders into a sorted PDF path list."""
    discovered: list[Path] = []
    for raw_input in inputs:
        path = Path(raw_input)
        if path.is_dir():
            discovered.extend(sorted(child for child in path.iterdir() if child.suffix.lower() == ".pdf"))
        else:
            discovered.append(path)
    return sorted(dict.fromkeys(discovered))


def main() -> int:
    """Run the CLI."""
    args = parse_args()
    configure_logging(args.debug)
    logger = logging.getLogger(__name__)

    pdf_files = expand_input_paths(args.inputs)
    if not pdf_files:
        logger.error("No PDF files found in the provided inputs.")
        return 1

    all_rows: list[dict[str, object]] = []

    for pdf_path in pdf_files:
        logger.info("Processing %s", pdf_path)
        text = extract_text_from_pdf(pdf_path)
        rows = parse_transactions(
            text=text,
            source_file=pdf_path,
            currency_filter=args.currency_filter,
        )
        logger.info("Extracted %s transactions from %s", len(rows), pdf_path.name)
        all_rows.extend(rows)

    if not all_rows:
        logger.warning("No transactions found.")
        return 0

    all_rows.sort(
        key=lambda row: (
            str(row["statement_close_date"]),
            str(row["source_file"]),
            str(row["transaction_date"]),
            int(row["source_line_no"]),
        )
    )
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_transactions_csv(all_rows, output_path, use_pandas=args.use_pandas)
    logger.info("CSV generated at %s with %s transactions", args.output, len(all_rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
