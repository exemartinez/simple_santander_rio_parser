# Simple Santander Rio Parser

English and Spanish guide for the Santander Rio VISA PDF parser CLI.

## English

### What this tool does

This CLI reads Santander Rio VISA credit card statement PDFs and exports the detected transactions to a CSV file.

Current capabilities:
- Reads one or many PDF files.
- Accepts a folder containing PDF statements.
- Detects ARS and USD billed transactions.
- Detects EUR purchases billed in USD.
- Infers full transaction dates using the statement closing date.
- Avoids headers, totals, balances, taxes, and repeated summary sections.
- Removes duplicate lines when the same transaction appears twice in extracted text.
- Writes a timestamped CSV file into the `output/` folder by default.

### Project structure

- `main.py`: CLI entrypoint
- `santander_visa_parser/pdf_reader.py`: PDF text extraction
- `santander_visa_parser/models.py`: shared data models
- `santander_visa_parser/credit_card_account_summary_format.py`: strategy interface
- `santander_visa_parser/santander_rio_visa_summary.py`: Santander Rio VISA strategy implementation
- `santander_visa_parser/transaction_parser.py`: strategy context
- `santander_visa_parser/csv_writer.py`: CSV writing
- `sources/`: sample input PDFs
- `output/`: generated CSV files

### Requirements

- Python 3.9 or newer
- A terminal
- Santander Rio VISA PDF statements

### Setup on a layman machine

If Python is not installed:
1. Install Python 3 from https://www.python.org/downloads/
2. During installation, make sure Python is added to the system PATH if the installer offers that option.

Download or copy this project to your machine, then open a terminal in the project folder.

Create a virtual environment:

```bash
python3 -m venv venv_visa_parser
```

Activate it:

macOS / Linux:

```bash
source venv_visa_parser/bin/activate
```

Windows PowerShell:

```powershell
venv_visa_parser\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Optional:
- Install `pandas` only if you want CSV export through `--use-pandas`.

```bash
pip install pandas
```

### How to run

Run against the `sources/` folder:

```bash
python main.py sources
```

Run against one PDF:

```bash
python main.py "sources/Resumen de tarjeta de crédito VISA-13-03-2026.pdf"
```

Run against many PDFs:

```bash
python main.py file1.pdf file2.pdf file3.pdf
```

Choose a custom output file:

```bash
python main.py sources -o output/my_transactions.csv
```

Enable debug logs:

```bash
python main.py sources --debug
```

Only keep ARS transactions:

```bash
python main.py sources --currency-filter ARS
```

Only keep USD transactions:

```bash
python main.py sources --currency-filter USD
```

Use pandas for export:

```bash
python main.py sources --use-pandas
```

### Default output

If `-o` is not provided, the CLI generates a timestamped CSV file with this format:

```text
output/movimientos__YYYY_MM_DD__HH_MM_SS.csv
```

Example:

```text
output/movimientos__2026_03_17__22_36_22.csv
```

### CLI options

- `inputs`: one or more PDF files or folders
- `-o`, `--output`: custom output CSV path
- `--debug`: shows skipped lines and parser diagnostics
- `--use-pandas`: exports using pandas if installed
- `--currency-filter ARS|USD`: keeps only billed transactions in the selected currency

### Typical workflow

1. Put your statement PDFs in a folder.
2. Run `python main.py <folder>`.
3. Open the generated CSV file from the `output/` folder.
4. Analyze the CSV in Excel, Numbers, LibreOffice, pandas, or another tool.

### Notes

- This parser is tailored to Santander Rio VISA statement formats.
- PDF text extraction quality depends on how readable the PDF content is.
- If the bank changes the statement layout, the parsing strategy may need adjustments.

## Español

### Que hace esta herramienta

Esta CLI lee PDFs de resúmenes de tarjeta Santander Rio VISA y exporta las transacciones detectadas a un archivo CSV.

Capacidades actuales:
- Lee uno o varios archivos PDF.
- Acepta una carpeta con resúmenes en PDF.
- Detecta transacciones facturadas en ARS y USD.
- Detecta compras en EUR facturadas en USD.
- Infiera la fecha completa de cada transacción usando la fecha de cierre.
- Evita encabezados, totales, saldos, impuestos y secciones repetidas del resumen.
- Elimina duplicados si la misma línea aparece dos veces en el texto extraído.
- Genera por defecto un CSV con timestamp dentro de la carpeta `output/`.

### Estructura del proyecto

- `main.py`: punto de entrada de la CLI
- `santander_visa_parser/pdf_reader.py`: extracción de texto del PDF
- `santander_visa_parser/models.py`: modelos compartidos
- `santander_visa_parser/credit_card_account_summary_format.py`: interfaz de estrategia
- `santander_visa_parser/santander_rio_visa_summary.py`: implementación concreta para Santander Rio VISA
- `santander_visa_parser/transaction_parser.py`: contexto de la estrategia
- `santander_visa_parser/csv_writer.py`: escritura del CSV
- `sources/`: PDFs de ejemplo
- `output/`: CSVs generados

### Requisitos

- Python 3.9 o superior
- Una terminal
- PDFs de resúmenes Santander Rio VISA

### Preparacion en una maquina comun

Si Python no esta instalado:
1. Instale Python 3 desde https://www.python.org/downloads/
2. Durante la instalacion, asegurese de marcar la opcion para agregar Python al PATH si el instalador la ofrece.

Descargue o copie este proyecto en su maquina y abra una terminal dentro de la carpeta del proyecto.

Crear un entorno virtual:

```bash
python3 -m venv venv_visa_parser
```

Activarlo:

macOS / Linux:

```bash
source venv_visa_parser/bin/activate
```

Windows PowerShell:

```powershell
venv_visa_parser\Scripts\Activate.ps1
```

Instalar dependencias:

```bash
pip install -r requirements.txt
```

Opcional:
- Instale `pandas` solo si quiere exportar usando `--use-pandas`.

```bash
pip install pandas
```

### Como ejecutar

Ejecutar contra la carpeta `sources/`:

```bash
python main.py sources
```

Ejecutar contra un PDF:

```bash
python main.py "sources/Resumen de tarjeta de credito VISA-13-03-2026.pdf"
```

Ejecutar contra varios PDFs:

```bash
python main.py archivo1.pdf archivo2.pdf archivo3.pdf
```

Elegir un archivo de salida personalizado:

```bash
python main.py sources -o output/mis_movimientos.csv
```

Activar logs de debug:

```bash
python main.py sources --debug
```

Filtrar solo transacciones ARS:

```bash
python main.py sources --currency-filter ARS
```

Filtrar solo transacciones USD:

```bash
python main.py sources --currency-filter USD
```

Usar pandas para exportar:

```bash
python main.py sources --use-pandas
```

### Salida por defecto

Si no se informa `-o`, la CLI genera un CSV con el siguiente formato:

```text
output/movimientos__YYYY_MM_DD__HH_MM_SS.csv
```

Ejemplo:

```text
output/movimientos__2026_03_17__22_36_22.csv
```

### Opciones de la CLI

- `inputs`: uno o mas archivos PDF o carpetas
- `-o`, `--output`: ruta personalizada del CSV de salida
- `--debug`: muestra lineas omitidas y diagnostico del parser
- `--use-pandas`: exporta usando pandas si esta instalado
- `--currency-filter ARS|USD`: conserva solo transacciones facturadas en la moneda elegida

### Flujo habitual

1. Coloque sus PDFs de resumen en una carpeta.
2. Ejecute `python main.py <carpeta>`.
3. Abra el CSV generado dentro de `output/`.
4. Analice el CSV en Excel, Numbers, LibreOffice, pandas u otra herramienta.

### Notas

- Este parser esta orientado al formato de resúmenes Santander Rio VISA.
- La calidad de extracción depende de cuan legible sea el contenido interno del PDF.
- Si el banco cambia el formato del resumen, puede ser necesario ajustar la estrategia de parsing.

## Releases

### Version 0.7

- Release date: `2026-03-17`
- Initial production-grade CLI refactor
- Strategy Pattern introduced through `CreditCardAccountSummaryFormat`
- Santander Rio VISA parser extracted into its own implementation
- Object-oriented architecture across parser, PDF reader, writer, and CLI
- Timestamped output file names in `output/`
- Improved handling for multiline descriptions, duplicate lines, USD/EUR detection, and debug logging
