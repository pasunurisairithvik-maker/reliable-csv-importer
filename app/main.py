import logging
import os
import sqlite3
from pathlib import Path
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import HTMLResponse
from app.importer import MAX_BYTES, InvalidCSV, import_csv, list_products

logger = logging.getLogger("inventory")

def create_app(db_path=None):
    application = FastAPI(title="Reliable CSV Importer", version="1.0.0")
    path = db_path or os.environ.get("INVENTORY_DB", "data/inventory.db")

    @application.get("/", response_class=HTMLResponse)
    def home():
        return (Path(__file__).parent / "index.html").read_text(encoding="utf-8")

    @application.post("/imports")
    def upload(file: UploadFile = File(...)):
        raw = file.file.read(MAX_BYTES + 1)
        try:
            result = import_csv(raw, path)
        except InvalidCSV as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except sqlite3.Error as exc:
            logger.error("import_failed", extra={"error_type": type(exc).__name__})
            raise HTTPException(status_code=503, detail="Database unavailable; retry later") from exc
        logger.info("import_complete", extra={"accepted": result["accepted"], "rejected": result["rejected"], "skipped": result["skipped"]})
        return result

    @application.get("/products")
    def products(limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)):
        try:
            return list_products(path, limit, offset)
        except sqlite3.Error as exc:
            raise HTTPException(status_code=503, detail="Database unavailable") from exc

    return application

app = create_app()
