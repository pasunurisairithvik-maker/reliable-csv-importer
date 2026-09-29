"""Validate inventory files and atomically insert valid records into SQLite."""
import csv
import io
import sqlite3
from decimal import Decimal, InvalidOperation
from pathlib import Path

REQUIRED = {"product_id", "name", "price", "quantity"}
MAX_BYTES = 2 * 1024 * 1024

class InvalidCSV(ValueError):
    """A whole-file error; no rows have been imported."""


def connect(db_path):
    if str(db_path) != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA busy_timeout=10000")
    con.execute("""CREATE TABLE IF NOT EXISTS inventory (
        product_id TEXT PRIMARY KEY, name TEXT NOT NULL,
        price_cents INTEGER NOT NULL CHECK(price_cents >= 0),
        quantity INTEGER NOT NULL CHECK(quantity >= 0))""")
    con.commit()
    return con


def parse_rows(raw):
    if len(raw) > MAX_BYTES:
        raise InvalidCSV("File exceeds the 2 MiB limit")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise InvalidCSV("Use a UTF-8 CSV file") from exc
    reader = csv.DictReader(io.StringIO(text, newline=""), strict=True)
    try:
        headers = reader.fieldnames
        if not headers or len(headers) != len(set(headers)) or set(headers) != REQUIRED:
            raise InvalidCSV("Columns must be product_id,name,price,quantity (any order)")
        # Read the entire file before writes so malformed quoting cannot partially import.
        return list(reader)
    except csv.Error as exc:
        raise InvalidCSV("Malformed CSV quoting") from exc


def validate(row):
    if None in row or any(value is None for value in row.values()):
        raise ValueError("Incorrect number of fields")
    product_id, name = row["product_id"].strip(), row["name"].strip()
    if not product_id or len(product_id) > 100:
        raise ValueError("product_id must contain 1-100 characters")
    if not name or len(name) > 200:
        raise ValueError("name must contain 1-200 characters")
    try:
        price = Decimal(row["price"].strip())
    except InvalidOperation as exc:
        raise ValueError("price must be a number") from exc
    if not price.is_finite() or price < 0 or price > Decimal("1000000000"):
        raise ValueError("price must be finite and between 0 and 1000000000")
    if price != price.quantize(Decimal("0.01")):
        raise ValueError("price must have at most two decimal places")
    try:
        quantity = int(row["quantity"].strip())
    except ValueError as exc:
        raise ValueError("quantity must be an integer") from exc
    if not 0 <= quantity <= 1000000000:
        raise ValueError("quantity must be between 0 and 1000000000")
    return product_id, name, int(price * 100), quantity


def import_csv(raw, db_path):
    rows = parse_rows(raw)
    result = {"total": len(rows), "accepted": 0, "skipped": 0, "rejected": 0, "issues": []}
    con = connect(db_path)
    try:
        with con:  # SQL failures roll back the entire import, including earlier inserts.
            for record, row in enumerate(rows, start=1):
                try:
                    values = validate(row)
                except ValueError as exc:
                    result["rejected"] += 1
                    result["issues"].append({"record": record, "status": "rejected", "reason": str(exc)})
                    continue
                existing = con.execute("SELECT * FROM inventory WHERE product_id=?", (values[0],)).fetchone()
                if existing:
                    if tuple(existing) == values:
                        result["skipped"] += 1
                        result["issues"].append({"record": record, "status": "skipped", "reason": "Identical product already exists"})
                    else:
                        result["rejected"] += 1
                        result["issues"].append({"record": record, "status": "rejected", "reason": "product_id conflicts with existing values"})
                    continue
                con.execute("INSERT INTO inventory VALUES (?,?,?,?)", values)
                result["accepted"] += 1
        return result
    finally:
        con.close()


def list_products(db_path, limit=100, offset=0):
    con = connect(db_path)
    try:
        return [dict(row) for row in con.execute(
            "SELECT * FROM inventory ORDER BY product_id LIMIT ? OFFSET ?", (limit, offset))]
    finally:
        con.close()
