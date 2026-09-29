# Reliable CSV Importer
A small Python application that validates inventory CSV files, inserts valid rows into SQLite, and reports invalid or duplicate records. It includes a browser upload form and an HTTP API.

## Run (Python 3.11 or newer)
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
Open http://127.0.0.1:8000. Interactive API docs: http://127.0.0.1:8000/docs.
Upload `examples/inventory.csv`: first upload accepts 3 rows, skips 1 identical duplicate, rejects 2 invalid rows. A second upload accepts 0, skips 4, rejects 2.

## Design decisions
- Columns: product_id,name,price,quantity. Order does not matter; extra/missing/duplicate columns are whole-file errors.
- UTF-8 only; 2 MiB file limit. Record numbers refer to CSV records, not physical lines when quoted fields span lines.
- Money is parsed with Decimal and stored as integer cents to avoid floating-point rounding.
- Same ID + same values: skip. Same ID + changed values: reject; never silently update existing inventory.
- Each import is one transaction. Database errors roll back all inserts from that request. Invalid individual records are rejected while valid records are kept.
- SQL uses parameters. GET /products supports limit and offset.
- Tests inject database failure, check rollback and repeat uploads, and cover the HTTP routes.

## Verify
```bash
python -m unittest discover -s tests -v
python benchmark.py
```
`results/benchmark.json` contains measured timings from three repeats per size. Read the machine details before comparing results.

## Scope and limits
Local learning demo, not a public production service. No authentication, robust concurrency policy, streaming processing, audit history, or malware scanning. Simultaneous overlapping imports may fail and require retry. The application-level size check is not a substitute for a reverse-proxy upload limit. There is no AWS integration.

## Student ownership
Built with AI assistance. Before using this on a resume, run it, read each function, and make an independently understood change. Read STUDENT_GUIDE.md. Do not claim authorship of untouched generated code or production usage.
