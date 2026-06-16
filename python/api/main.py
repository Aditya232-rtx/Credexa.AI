from __future__ import annotations

import sqlite3
import sys
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

BASE_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = BASE_DIR.parent
sys.path.insert(0, str(BASE_DIR))

from mock_gov_apis.main import router as mock_gov_router
from services.case_pipeline import CasePipeline

DB_PATH = BASE_DIR / "credexa.db"
SCHEMA_PATH = BASE_DIR / "db" / "schema.sql"
UPLOAD_ROOT = BASE_DIR / "uploads"
DOCUMENT_TYPES_PATH = ROOT_DIR / "documenttypes.md"

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="Credexa AI - API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(mock_gov_router)
pipeline = CasePipeline(BASE_DIR, DB_PATH, DOCUMENT_TYPES_PATH)


def get_db() -> sqlite3.Connection:
    if not DB_PATH.exists() or DB_PATH.stat().st_size == 0:
        init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))





@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/metadata/document-types")
def document_types() -> dict:
    return {"categories": list(pipeline.router.taxonomy.keys()), "taxonomy": pipeline.router.taxonomy}


@app.post("/upload")
async def upload_documents(
    background_tasks: BackgroundTasks,
    applicant_name: str = Form(...),
    application_type: str = Form(...),
    application_subtype: str = Form(""),
    mobile_no: str = Form(""),
    address: str = Form(""),
    files: List[UploadFile] = File(...),
):
    case_id = f"CX-{str(uuid.uuid4())[:8].upper()}"
    case_dir = UPLOAD_ROOT / case_id
    case_dir.mkdir(parents=True, exist_ok=True)

    with get_db() as conn:
        conn.execute(
            "INSERT INTO cases (id, applicant_name, mobile_no, address, application_type, application_subtype, status, risk_score) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (case_id, applicant_name, mobile_no, address, application_type, application_subtype, "processing", 0),
        )

        saved_files = []
        for upload in files:
            if not upload.filename:
                raise HTTPException(status_code=400, detail="Filename cannot be empty")
            doc_id = str(uuid.uuid4())
            file_path = case_dir / upload.filename
            content = await upload.read()
            file_path.write_bytes(content)

            conn.execute(
                "INSERT INTO documents (id, case_id, file_name, file_type, file_size, doc_category, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (doc_id, case_id, upload.filename, upload.content_type or file_path.suffix, len(content), "Unknown", "uploaded"),
            )
            saved_files.append({"id": doc_id, "name": upload.filename})

        conn.commit()

    background_tasks.add_task(pipeline.process_case, case_id)
    return {"case_id": case_id, "status": "processing", "files": saved_files}


@app.get("/cases")
def get_cases() -> dict:
    with get_db() as conn:
        cases = conn.execute("SELECT * FROM cases ORDER BY submitted_at DESC").fetchall()
        return {"cases": [dict(row) for row in cases]}


@app.get("/cases/{case_id}")
def get_case(case_id: str) -> dict:
    with get_db() as conn:
        case = conn.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")

        documents = conn.execute("SELECT * FROM documents WHERE case_id = ?", (case_id,)).fetchall()
        flags = conn.execute(
            "SELECT f.* FROM flags f LEFT JOIN documents d ON d.id = f.document_id WHERE d.case_id = ? OR f.document_id IS NULL",
            (case_id,),
        ).fetchall()
        audit_log = conn.execute("SELECT * FROM audit_log WHERE case_id = ? ORDER BY created_at DESC", (case_id,)).fetchall()

        return {
            "case": dict(case),
            "documents": [dict(doc) for doc in documents],
            "flags": [dict(flag) for flag in flags],
            "audit_log": [dict(entry) for entry in audit_log],
        }


@app.post("/cases/{case_id}/analyze")
def analyze_case(case_id: str) -> dict:
    try:
        return pipeline.process_case(case_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
