from __future__ import annotations

import sys
import uuid
import os
import mimetypes
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, Depends, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security.api_key import APIKeyHeader
from psycopg2.extras import RealDictCursor
from pydantic import BaseModel
from loguru import logger

BASE_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = BASE_DIR.parent
sys.path.insert(0, str(BASE_DIR))

from utils.encryption import encrypt_data, encrypt_string, decrypt_string
from db.connection import get_db_connection

from mock_gov_apis.main import router as mock_gov_router
from tasks import process_case_task

SCHEMA_PATH = BASE_DIR / "db" / "schema.sql"
UPLOAD_ROOT = BASE_DIR / "uploads"
DOCUMENT_TYPES_PATH = ROOT_DIR / "docs" / "documenttypes.md"

DB_DSN = os.environ.get("DB_DSN", "dbname=credexa user=adityajadhav host=localhost port=5432")


def init_db() -> None:
    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    with get_db_connection() as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(SCHEMA_PATH.read_text(encoding="utf-8"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


api_key_header = APIKeyHeader(name="x-api-key", auto_error=False)

def get_api_key(api_key: str = Security(api_key_header)):
    expected = os.environ.get("CREDEXA_API_KEY")
    if expected and api_key != expected:
        raise HTTPException(status_code=403, detail="Could not validate API Key")
    return api_key

app = FastAPI(title="Credexa AI - API", lifespan=lifespan, dependencies=[Depends(get_api_key)])
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(mock_gov_router)


# ─── Health ───────────────────────────────────────────────────────────────────

@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


# ─── Metadata ─────────────────────────────────────────────────────────────────

@app.get("/metadata/document-types")
def document_types() -> dict:
    import re as _re
    taxonomy: dict = {}
    if DOCUMENT_TYPES_PATH.exists():
        current_category = None
        for line in DOCUMENT_TYPES_PATH.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            # Match: ## **1. Land & Property Records**
            if stripped.startswith("## ") and "**" in stripped:
                cat = stripped.replace("## ", "").replace("**", "").strip()
                cat = _re.sub(r"^\d+\.\s*", "", cat).strip()
                current_category = cat
                taxonomy[current_category] = []
            # Match: - **Sale Deed (Deed of Conveyance):** description
            elif stripped.startswith("- **") and current_category:
                inner = stripped[4:]
                name = inner.split("**")[0].rstrip(":").strip()
                if name:
                    taxonomy[current_category].append(name)
    return {"categories": list(taxonomy.keys()), "taxonomy": taxonomy}


# ─── Upload ───────────────────────────────────────────────────────────────────

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

    ALLOWED_MIME_TYPES = {
        "application/pdf",
        "image/jpeg",
        "image/png",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel",
    }

    with get_db_connection() as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO cases (id, applicant_name, mobile_no, address, application_type, application_subtype, status, risk_score) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (case_id, applicant_name, encrypt_string(mobile_no), encrypt_string(address), application_type, application_subtype, "processing", 0),
            )

            saved_files = []
            for upload in files:
                if not upload.filename:
                    raise HTTPException(status_code=400, detail="Filename cannot be empty")

                mime_type, _ = mimetypes.guess_type(upload.filename)
                if mime_type not in ALLOWED_MIME_TYPES and upload.content_type not in ALLOWED_MIME_TYPES:
                    raise HTTPException(status_code=400, detail=f"Unsupported file type: {upload.filename}")

                content = await upload.read()
                if len(content) > 50 * 1024 * 1024:
                    raise HTTPException(status_code=400, detail=f"File {upload.filename} too large (max 50MB)")

                doc_id = str(uuid.uuid4())
                file_path = case_dir / f"{doc_id}.enc"
                encrypted_content = encrypt_data(content)
                file_path.write_bytes(encrypted_content)

                cur.execute(
                    "INSERT INTO documents (id, case_id, file_name, file_type, file_size, doc_category, status) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    (doc_id, case_id, upload.filename, upload.content_type or Path(upload.filename).suffix, len(content), "Unknown", "uploaded"),
                )
                saved_files.append({"id": doc_id, "name": upload.filename})

    process_case_task.delay(case_id)
    return {"case_id": case_id, "status": "processing", "files": saved_files}


# ─── Cases ────────────────────────────────────────────────────────────────────

@app.get("/cases")
def get_cases() -> dict:
    with get_db_connection() as conn:
        conn.autocommit = True
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM cases ORDER BY submitted_at DESC")
            cases = cur.fetchall()
            cases_list = []
            for row in cases:
                d = dict(row)
                d["mobile_no"] = decrypt_string(d.get("mobile_no", ""))
                d["address"] = decrypt_string(d.get("address", ""))
                cases_list.append(d)
            return {"cases": cases_list}


@app.get("/cases/{case_id}")
def get_case(case_id: str) -> dict:
    with get_db_connection() as conn:
        conn.autocommit = True
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM cases WHERE id = %s", (case_id,))
            case = cur.fetchone()
            if not case:
                raise HTTPException(status_code=404, detail="Case not found")

            case_dict = dict(case)
            case_dict["mobile_no"] = decrypt_string(case_dict.get("mobile_no", ""))
            case_dict["address"] = decrypt_string(case_dict.get("address", ""))

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
                "case": case_dict,
                "documents": [dict(doc) for doc in documents],
                "flags": [dict(flag) for flag in flags],
                "audit_log": [dict(entry) for entry in audit_log],
            }


@app.post("/cases/{case_id}/analyze")
def analyze_case(case_id: str) -> dict:
    process_case_task.delay(case_id)
    return {"status": "enqueued", "case_id": case_id}

class FeedbackIn(BaseModel):
    decision: str
    reviewer_id: str
    notes: str = ""

@app.post("/cases/{case_id}/feedback")
def submit_feedback(case_id: str, feedback: FeedbackIn) -> dict:
    import uuid
    fid = str(uuid.uuid4())
    with get_db_connection() as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO feedback (id, case_id, reviewer_id, decision, notes) VALUES (%s, %s, %s, %s, %s) RETURNING id",
                (fid, case_id, feedback.reviewer_id, feedback.decision, feedback.notes),
            )
            inserted_id = cur.fetchone()[0]
            if feedback.decision.lower() in ("approved", "rejected"):
                new_status = feedback.decision.lower()
                cur.execute("UPDATE cases SET status = %s WHERE id = %s", (new_status, case_id))
            return {"status": "success", "feedback_id": inserted_id}

@app.get("/cases/{case_id}/feedback")
def get_feedback(case_id: str) -> dict:
    with get_db_connection() as conn:
        conn.autocommit = True
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM feedback WHERE case_id = %s ORDER BY created_at DESC", (case_id,))
            feedbacks = cur.fetchall()
            return {"feedback": [dict(f) for f in feedbacks]}
