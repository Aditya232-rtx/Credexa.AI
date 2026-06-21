from __future__ import annotations

import sys
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
from psycopg2.extras import RealDictCursor

BASE_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = BASE_DIR.parent
sys.path.insert(0, str(BASE_DIR))

from mock_gov_apis.main import router as mock_gov_router
from tasks import process_case_task

SCHEMA_PATH = BASE_DIR / "db" / "schema.sql"
UPLOAD_ROOT = BASE_DIR / "uploads"
DOCUMENT_TYPES_PATH = ROOT_DIR / "documenttypes.md"

DB_DSN = "dbname=credexa user=adityajadhav host=localhost port=5432"

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

def get_db() -> psycopg2.extensions.connection:
    conn = psycopg2.connect(DB_DSN)
    conn.autocommit = True
    return conn

def init_db() -> None:
    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(SCHEMA_PATH.read_text(encoding="utf-8"))

@app.get("/health")
def health() -> dict:
    return {"status": "ok"}

@app.get("/metadata/document-types")
def document_types() -> dict:
    # Since we moved pipeline to tasks.py, we can just load the document taxonomy directly or instantiate a lightweight reader
    taxonomy = {}
    if DOCUMENT_TYPES_PATH.exists():
        current_category = None
        for line in DOCUMENT_TYPES_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("- **") and "**:" in line:
                cat = line.replace("- **", "").split("**:")[0].strip()
                current_category = cat
                taxonomy[current_category] = []
            elif line.startswith("- ") and current_category:
                doc_type = line.replace("- ", "").strip()
                taxonomy[current_category].append(doc_type)
    return {"categories": list(taxonomy.keys()), "taxonomy": taxonomy}

@app.post("/upload")
async def upload_documents(
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
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO cases (id, applicant_name, mobile_no, address, application_type, application_subtype, status, risk_score) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
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

                cur.execute(
                    "INSERT INTO documents (id, case_id, file_name, file_type, file_size, doc_category, status) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    (doc_id, case_id, upload.filename, upload.content_type or file_path.suffix, len(content), "Unknown", "uploaded"),
                )
                saved_files.append({"id": doc_id, "name": upload.filename})

    # Trigger Celery Task
    process_case_task.delay(case_id)
    return {"case_id": case_id, "status": "processing", "files": saved_files}

@app.get("/cases")
def get_cases() -> dict:
    with get_db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM cases ORDER BY submitted_at DESC")
            cases = cur.fetchall()
            return {"cases": [dict(row) for row in cases]}

@app.get("/cases/{case_id}")
def get_case(case_id: str) -> dict:
    with get_db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM cases WHERE id = %s", (case_id,))
            case = cur.fetchone()
            if not case:
                raise HTTPException(status_code=404, detail="Case not found")

            cur.execute("SELECT * FROM documents WHERE case_id = %s", (case_id,))
            documents = cur.fetchall()
            
            cur.execute(
                "SELECT f.* FROM flags f LEFT JOIN documents d ON d.id = f.document_id WHERE d.case_id = %s OR f.document_id IS NULL",
                (case_id,),
            )
            flags = cur.fetchall()
            
            cur.execute("SELECT * FROM audit_log WHERE case_id = %s ORDER BY created_at DESC", (case_id,))
            audit_log = cur.fetchall()

            return {
                "case": dict(case),
                "documents": [dict(doc) for doc in documents],
                "flags": [dict(flag) for flag in flags],
                "audit_log": [dict(entry) for entry in audit_log],
            }

@app.post("/cases/{case_id}/analyze")
def analyze_case(case_id: str) -> dict:
    # We can just enqueue it again via Celery
    process_case_task.delay(case_id)
    return {"status": "enqueued", "case_id": case_id}

