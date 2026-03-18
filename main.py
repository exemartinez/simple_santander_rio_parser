"""CLI entrypoint for credit card and account statement PDF extraction."""

from __future__ import annotations

import argparse
import logging
from datetime import datetime
from pathlib import Path

from santander_visa_parser.csv_writer import TransactionCSVWriter
from santander_visa_parser.format_registry import StatementFormatRegistry
from santander_visa_parser.pdf_reader import PDFTextReader
from santander_visa_parser.transaction_parser import TransactionParser


class CLIArguments:
    """Command-line argument builder."""

    def __init__(self) -> None:
        format_registry = StatementFormatRegistry()
        self.parser = argparse.ArgumentParser(
            description="Extract normalized transactions from supported PDF statements into CSV."
        )
        self.parser.add_argument("inputs", nargs="+", help="PDF files and/or folders containing PDFs.")
        self.parser.add_argument(
            "-o",
            "--output",
            default=self._default_output_path(),
            help="Output CSV path.",
        )
        self.parser.add_argument(
            "--debug",
            action="store_true",
            help="Enable debug logging for skipped lines.",
        )
        self.parser.add_argument(
            "--use-pandas",
            action="store_true",
            help="Use pandas to build the CSV output when pandas is available.",
        )
        self.parser.add_argument(
            "--currency-filter",
            choices=("ARS", "USD"),
            help="Keep only transactions billed in the selected currency.",
        )
        self.parser.add_argument(
            "--format",
            default="auto",
            choices=("auto", *format_registry.names()),
            help="Statement format to use. Defaults to auto-detection.",
        )

    def parse(self) -> argparse.Namespace:
        """Parse command-line arguments."""
        return self.parser.parse_args()

    def _default_output_path(self) -> str:
        """Build the default timestamped output file path."""
        timestamp = datetime.now().strftime("%Y_%m_%d__%H_%M_%S")
        return f"output/movimientos__{timestamp}.csv"


class LoggingConfigurator:
    """Configure application logging."""

    def configure(self, debug: bool) -> None:
        """Configure root logging."""
        logging.basicConfig(
            level=logging.DEBUG if debug else logging.INFO,
            format="%(levelname)s %(message)s",
        )


class PDFPathCollector:
    """Expand CLI inputs into a list of PDF files."""

    def collect(self, inputs: list[str]) -> list[Path]:
        """Expand input files and folders into a sorted PDF path list."""
        discovered: list[Path] = []
        for raw_input in inputs:
            path = Path(raw_input)
            if path.is_dir():
                discovered.extend(
                    sorted(child for child in path.iterdir() if child.suffix.lower() == ".pdf")
                )
            else:
                discovered.append(path)
        return sorted(dict.fromkeys(discovered))


class StatementExtractionApplication:
    """Application service coordinating PDF extraction and CSV writing."""

    def __init__(
        self,
        text_reader: PDFTextReader,
        format_registry: StatementFormatRegistry,
        csv_writer: TransactionCSVWriter,
    ) -> None:
        self.text_reader = text_reader
        self.format_registry = format_registry
        self.csv_writer = csv_writer
        self.logger = logging.getLogger(__name__)

    def run(self, args: argparse.Namespace) -> int:
        """Run the extraction workflow."""
        pdf_files = PDFPathCollector().collect(args.inputs)
        if not pdf_files:
            self.logger.error("No PDF files found in the provided inputs.")
            return 1

        all_rows: list[dict[str, object]] = []

        for pdf_path in pdf_files:
            self.logger.info("Processing %s", pdf_path)
            text = self.text_reader.extract_text(pdf_path)
            selected_format_name, parser_format = self.format_registry.resolve(
                args.format,
                text=text,
                source_file=pdf_path,
            )
            self.logger.info("Using format %s for %s", selected_format_name, pdf_path.name)
            rows = TransactionParser(parser_format).parse(
                text=text,
                source_file=pdf_path,
                currency_filter=args.currency_filter,
            )
            self.logger.info("Extracted %s transactions from %s", len(rows), pdf_path.name)
            all_rows.extend(rows)

        if not all_rows:
            self.logger.warning("No transactions found.")
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
        self.csv_writer.write(all_rows, output_path, use_pandas=args.use_pandas)
        self.logger.info("CSV generated at %s with %s transactions", args.output, len(all_rows))
        return 0


def main() -> int:
    """Run the CLI."""
    args = CLIArguments().parse()
    LoggingConfigurator().configure(args.debug)
    application = StatementExtractionApplication(
        text_reader=PDFTextReader(),
        format_registry=StatementFormatRegistry(),
        csv_writer=TransactionCSVWriter(),
    )
    return application.run(args)


if __name__ == "__main__":
    raise SystemExit(main())
