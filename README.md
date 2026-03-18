# Simple Statement Parser

This whole project was generated with Cortex Agents under Pycharm.
English and Spanish guide for the PDF statement to CSV CLI.

## English

### What this tool does

This CLI reads supported PDF statements, extracts normalized movements or card transactions, and writes them to a single CSV file.

It currently supports:
- Santander Rio VISA credit card statements
- Banco Galicia VISA credit card statements
- Banco Galicia Mastercard credit card statements
- MercadoPago account summaries

The goal is simple:
- You give the CLI one or more PDFs or folders
- The CLI detects the correct statement format, unless you explicitly force one
- It extracts rows into a shared schema
- It writes one CSV output file

### What the output contains

The CSV output uses one normalized structure for every supported format.

Common columns include:
- `source_file`
- `statement_close_date`
- `transaction_date`
- `description`
- `currency`
- `amount`
- `ars_amount`
- `usd_amount`
- `original_currency`
- `original_amount`
- `installment`
- `reference`
- `source_line_no`
- `raw_line`

This means the tool is intended for later analysis in Excel, Numbers, LibreOffice, pandas, DuckDB, or any other tabular workflow.

### Current capabilities

- Reads one PDF or many PDFs in one run
- Accepts one or many folders
- Merges all extracted rows into one CSV
- Uses auto-detection by default across the supported formats
- Allows explicit format selection when auto-detection is not desired
- Keeps the default timestamped output naming
- Supports a custom output path with `-o`
- Supports optional `pandas` CSV export
- Supports billed currency filtering with `--currency-filter`
- Preserves the original extracted line for auditability
- Skips headers, totals, taxes, balance sections, and summary blocks when the format parser knows how to identify them
- Handles multiline PDF extraction artifacts when needed by the concrete parser
- Sorts output rows consistently before writing

### Important usage model

This project follows one core idea:
- Generic CLI flow
- Format-specific parser strategies

In practice:
- `main.py` handles argument parsing, file collection, output writing, and execution flow
- Each statement format lives in its own parser class
- The format registry decides which parser to use

This matters because new formats should be added as isolated parser implementations, not as condition-heavy patches inside one giant parser.

### Supported formats

- `auto`
  Uses text-based auto-detection. This is the recommended default for normal use.
- `santander-rio-visa`
  Forces the Santander Rio VISA parser.
- `galicia-visa`
  Forces the Banco Galicia VISA parser.
- `galicia-mastercard`
  Forces the Banco Galicia Mastercard parser.
- `mercadopago`
  Forces the MercadoPago account summary parser.

Use explicit format selection when:
- You are validating a parser
- You know the folder contains only one format
- You suspect a future statement layout change broke auto-detection

### Requirements

- Python 3.9 or newer
- A terminal
- Supported statement PDFs

### Setup

If Python is not installed:
1. Install Python 3 from https://www.python.org/downloads/
2. During installation, add Python to PATH if the installer offers that option.

Create a virtual environment:

```bash
python3 -m venv venv_visa_parser
```

Activate it.

macOS / Linux:

```bash
source venv_visa_parser/bin/activate
```

Windows PowerShell:

```powershell
venv_visa_parser\Scripts\Activate.ps1
```

Install the required dependencies:

```bash
pip install -r requirements.txt
```

Optional:

```bash
pip install pandas
```

Install `pandas` only if you want to use `--use-pandas`.

### Project structure

- `main.py`: CLI entrypoint
- `santander_visa_parser/pdf_reader.py`: PDF text extraction
- `santander_visa_parser/models.py`: shared normalized data models
- `santander_visa_parser/credit_card_account_summary_format.py`: parser strategy contract
- `santander_visa_parser/transaction_parser.py`: strategy wrapper
- `santander_visa_parser/format_registry.py`: format registry and auto-detection
- `santander_visa_parser/santander_rio_visa_summary.py`: Santander Rio VISA parser
- `santander_visa_parser/galicia_visa_summary.py`: Banco Galicia VISA parser
- `santander_visa_parser/galicia_mastercard_summary.py`: Banco Galicia Mastercard parser
- `santander_visa_parser/mercadopago_account_summary.py`: MercadoPago account summary parser
- `santander_visa_parser/csv_writer.py`: CSV writer
- `sources/`: sample input PDFs
- `output/`: generated CSV files

### How to run

Run against one folder with auto-detection:

```bash
python main.py sources
```

Run against one PDF:

```bash
python main.py "sources/Resumen de tarjeta de crédito VISA-13-03-2026.pdf"
```

Run against several PDFs:

```bash
python main.py file1.pdf file2.pdf file3.pdf
```

Run against several folders and files together:

```bash
python main.py sources other_folder one_file.pdf
```

Force Santander Rio VISA:

```bash
python main.py sources --format santander-rio-visa
```

Force Galicia VISA:

```bash
python main.py sources --format galicia-visa
```

Force Galicia Mastercard:

```bash
python main.py sources --format galicia-mastercard
```

Force MercadoPago:

```bash
python main.py sources --format mercadopago
```

Write to a custom output path:

```bash
python main.py sources -o output/my_transactions.csv
```

Enable debug logs:

```bash
python main.py sources --debug
```

Keep only ARS rows:

```bash
python main.py sources --currency-filter ARS
```

Keep only USD rows:

```bash
python main.py sources --currency-filter USD
```

Use pandas for CSV export:

```bash
python main.py sources --use-pandas
```

Combine several options:

```bash
python main.py sources --format auto --currency-filter ARS --debug --use-pandas
```

### Default output

If `-o` is not provided, the CLI writes a timestamped CSV file with this format:

```text
output/movimientos__YYYY_MM_DD__HH_MM_SS.csv
```

Example:

```text
output/movimientos__2026_03_17__23_06_35.csv
```

This default behavior remains the standard run mode.

### CLI options

- `inputs`
  One or more PDF files or folders containing PDFs.
- `-o`, `--output`
  Custom output CSV path. If omitted, the CLI writes a timestamped file in `output/`.
- `--debug`
  Enables parser diagnostics and skipped-line logging.
- `--use-pandas`
  Uses pandas for CSV writing when pandas is installed.
- `--currency-filter ARS|USD`
  Keeps only rows billed in the selected currency.
- `--format`
  Selects the parser format. Valid values are `auto`, `santander-rio-visa`, `galicia-visa`, `galicia-mastercard`, and `mercadopago`.

### Recommended workflow

1. Put the PDFs you want to process into a folder.
2. Run `python main.py <folder>`.
3. Let auto-detection choose the parser unless you have a specific reason to force a format.
4. Open the generated CSV in `output/`.
5. Filter, audit, and analyze from the normalized columns.

### Operational notes

- Auto-detection is the recommended normal mode.
- Explicit `--format` is better for parser validation and troubleshooting.
- The parser depends on PDF text extraction quality. If the PDF text layer changes significantly, the format-specific parser may need adjustment.
- Different statement families do not necessarily expose the same original fields, but they are all mapped into one shared normalized CSV schema.
- The `raw_line` column is intentionally preserved so you can audit suspicious rows against the extracted text.

### Limitations

- This is a text-extraction parser, not a full OCR pipeline.
- If a PDF has no usable text layer or the line order changes heavily, extraction quality may drop.
- Format support is explicit. Unsupported statement families will not parse correctly until a new parser strategy is added.

## Español

### Que hace esta herramienta

Esta CLI lee PDFs de resúmenes o cuentas compatibles, extrae movimientos o consumos normalizados y los escribe en un solo archivo CSV.

Actualmente soporta:
- Resúmenes de tarjeta Santander Rio VISA
- Resúmenes de tarjeta Banco Galicia VISA
- Resúmenes de tarjeta Banco Galicia Mastercard
- Resúmenes de cuenta de MercadoPago

La idea es simple:
- Usted entrega uno o varios PDFs o carpetas
- La CLI detecta el formato correcto, salvo que usted lo fuerce manualmente
- Extrae las filas en un esquema compartido
- Escribe un único CSV de salida

### Que contiene la salida

La salida CSV usa una estructura normalizada para todos los formatos soportados.

Columnas comunes:
- `source_file`
- `statement_close_date`
- `transaction_date`
- `description`
- `currency`
- `amount`
- `ars_amount`
- `usd_amount`
- `original_currency`
- `original_amount`
- `installment`
- `reference`
- `source_line_no`
- `raw_line`

Esto permite analizar el resultado en Excel, Numbers, LibreOffice, pandas, DuckDB u otra herramienta tabular.

### Capacidades actuales

- Lee un PDF o muchos PDFs en una sola ejecución
- Acepta una o varias carpetas
- Consolida todas las filas extraídas en un solo CSV
- Usa auto-detección por defecto entre los formatos soportados
- Permite seleccionar el formato manualmente cuando no se desea usar auto-detección
- Mantiene la salida por defecto con nombre timestamped
- Soporta ruta de salida personalizada con `-o`
- Soporta exportación opcional con `pandas`
- Soporta filtro por moneda facturada con `--currency-filter`
- Conserva la línea original extraída para auditoría
- Omite encabezados, totales, impuestos, saldos y secciones de resumen cuando el parser del formato sabe identificarlos
- Maneja artefactos de extracción multilinea cuando el parser concreto lo necesita
- Ordena consistentemente las filas antes de escribir el CSV

### Modelo de uso importante

Este proyecto sigue una idea central:
- Flujo genérico de CLI
- Estrategias de parsing específicas por formato

En la práctica:
- `main.py` maneja argumentos, descubrimiento de archivos, escritura de salida y flujo general
- Cada formato de resumen vive en su propia clase parser
- El registro de formatos decide qué parser usar

Esto importa porque los formatos nuevos deben agregarse como implementaciones aisladas, no como parches llenos de condicionales dentro de un solo parser gigante.

### Formatos soportados

- `auto`
  Usa auto-detección basada en el texto. Es la opción recomendada para el uso normal.
- `santander-rio-visa`
  Fuerza el parser de Santander Rio VISA.
- `galicia-visa`
  Fuerza el parser de Banco Galicia VISA.
- `galicia-mastercard`
  Fuerza el parser de Banco Galicia Mastercard.
- `mercadopago`
  Fuerza el parser del resumen de cuenta de MercadoPago.

Use selección explícita de formato cuando:
- Está validando un parser
- Sabe que la carpeta contiene un solo formato
- Sospecha que un cambio futuro en el layout rompió la auto-detección

### Requisitos

- Python 3.9 o superior
- Una terminal
- PDFs de resúmenes compatibles

### Preparacion

Si Python no está instalado:
1. Instale Python 3 desde https://www.python.org/downloads/
2. Durante la instalación, agregue Python al PATH si el instalador ofrece esa opción.

Crear un entorno virtual:

```bash
python3 -m venv venv_visa_parser
```

Activarlo.

macOS / Linux:

```bash
source venv_visa_parser/bin/activate
```

Windows PowerShell:

```powershell
venv_visa_parser\Scripts\Activate.ps1
```

Instalar las dependencias requeridas:

```bash
pip install -r requirements.txt
```

Opcional:

```bash
pip install pandas
```

Instale `pandas` solo si quiere usar `--use-pandas`.

### Estructura del proyecto

- `main.py`: punto de entrada de la CLI
- `santander_visa_parser/pdf_reader.py`: extracción de texto del PDF
- `santander_visa_parser/models.py`: modelos de datos normalizados
- `santander_visa_parser/credit_card_account_summary_format.py`: contrato de estrategia de parsing
- `santander_visa_parser/transaction_parser.py`: wrapper de estrategia
- `santander_visa_parser/format_registry.py`: registro de formatos y auto-detección
- `santander_visa_parser/santander_rio_visa_summary.py`: parser Santander Rio VISA
- `santander_visa_parser/galicia_visa_summary.py`: parser Banco Galicia VISA
- `santander_visa_parser/galicia_mastercard_summary.py`: parser Banco Galicia Mastercard
- `santander_visa_parser/mercadopago_account_summary.py`: parser MercadoPago
- `santander_visa_parser/csv_writer.py`: escritura del CSV
- `sources/`: PDFs de ejemplo
- `output/`: CSVs generados

### Como ejecutar

Ejecutar una carpeta con auto-detección:

```bash
python main.py sources
```

Ejecutar un PDF:

```bash
python main.py "sources/Resumen de tarjeta de credito VISA-13-03-2026.pdf"
```

Ejecutar varios PDFs:

```bash
python main.py archivo1.pdf archivo2.pdf archivo3.pdf
```

Ejecutar varias carpetas y archivos juntos:

```bash
python main.py sources otra_carpeta un_archivo.pdf
```

Forzar Santander Rio VISA:

```bash
python main.py sources --format santander-rio-visa
```

Forzar Galicia VISA:

```bash
python main.py sources --format galicia-visa
```

Forzar Galicia Mastercard:

```bash
python main.py sources --format galicia-mastercard
```

Forzar MercadoPago:

```bash
python main.py sources --format mercadopago
```

Escribir en una ruta personalizada:

```bash
python main.py sources -o output/mis_movimientos.csv
```

Activar logs de debug:

```bash
python main.py sources --debug
```

Conservar solo filas ARS:

```bash
python main.py sources --currency-filter ARS
```

Conservar solo filas USD:

```bash
python main.py sources --currency-filter USD
```

Usar pandas para exportar:

```bash
python main.py sources --use-pandas
```

Combinar varias opciones:

```bash
python main.py sources --format auto --currency-filter ARS --debug --use-pandas
```

### Salida por defecto

Si no se informa `-o`, la CLI escribe un CSV con timestamp usando este formato:

```text
output/movimientos__YYYY_MM_DD__HH_MM_SS.csv
```

Ejemplo:

```text
output/movimientos__2026_03_17__23_06_35.csv
```

Este comportamiento por defecto sigue siendo la forma estándar de ejecución.

### Opciones de la CLI

- `inputs`
  Uno o más archivos PDF o carpetas que contienen PDFs.
- `-o`, `--output`
  Ruta personalizada del CSV de salida. Si se omite, la CLI escribe un archivo timestamped dentro de `output/`.
- `--debug`
  Habilita diagnósticos del parser y logging de líneas omitidas.
- `--use-pandas`
  Usa pandas para escribir el CSV cuando pandas está instalado.
- `--currency-filter ARS|USD`
  Conserva solo filas facturadas en la moneda seleccionada.
- `--format`
  Selecciona el formato del parser. Valores válidos: `auto`, `santander-rio-visa`, `galicia-visa`, `galicia-mastercard` y `mercadopago`.

### Flujo recomendado

1. Coloque los PDFs que quiere procesar dentro de una carpeta.
2. Ejecute `python main.py <carpeta>`.
3. Deje que la auto-detección elija el parser, salvo que tenga una razón concreta para forzar un formato.
4. Abra el CSV generado dentro de `output/`.
5. Filtre, audite y analice desde las columnas normalizadas.

### Notas operativas

- La auto-detección es el modo normal recomendado.
- `--format` explícito es mejor para validación del parser y troubleshooting.
- El parser depende de la calidad de extracción de texto del PDF. Si el texto cambia mucho, puede ser necesario ajustar el parser específico del formato.
- Las distintas familias de resúmenes no necesariamente exponen los mismos campos originales, pero todas se mapean al mismo esquema CSV normalizado.
- La columna `raw_line` se conserva intencionalmente para auditar filas dudosas contra el texto extraído.

### Limitaciones

- Este proyecto es un parser basado en extracción de texto, no un pipeline OCR completo.
- Si un PDF no tiene una capa de texto utilizable o cambia mucho el orden de líneas, la calidad de extracción puede bajar.
- El soporte de formatos es explícito. Un resumen no soportado no se procesará correctamente hasta agregar una nueva estrategia de parser.

## Releases

### Version 0.8

- Release date: `2026-03-17`
- Multi-format support added
- Clean format entry through `--format`
- Auto-detection introduced through the statement format registry
- Added Banco Galicia VISA parser
- Added Banco Galicia Mastercard parser
- Added MercadoPago account summary parser
- Default timestamped output behavior preserved
- Mixed-folder processing validated into a single consolidated CSV

### Version 0.7

- Release date: `2026-03-17`
- Initial production-grade CLI refactor
- Strategy Pattern introduced through `CreditCardAccountSummaryFormat`
- Santander Rio VISA parser extracted into its own implementation
- Object-oriented architecture across parser, PDF reader, writer, and CLI
- Timestamped output file names in `output/`
- Improved handling for multiline descriptions, duplicate lines, USD/EUR detection, and debug logging
