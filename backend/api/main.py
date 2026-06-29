from __future__ import annotations

import uuid
import os
import mimetypes
import re
import secrets
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List
from datetime import datetime, timezone

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, Depends, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel, field_validator

from api.constants import FEEDBACK_DECISIONS
from loguru import logger

from utils.encryption import encrypt_data, encrypt_string, decrypt_string
from db.connection import get_db_connection, init_db, DB_BACKEND

def _cursor(conn):
    kwargs = {}
    if DB_BACKEND == "postgres":
        from psycopg2.extras import RealDictCursor
        kwargs["cursor_factory"] = RealDictCursor
    return conn.cursor(**kwargs)

from mock_gov_apis.main import router as mock_gov_router
from tasks import process_case_task

BASE_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BASE_DIR.parent
SCHEMA_PATH = BASE_DIR / "db" / "schema.sql"
UPLOAD_ROOT = BASE_DIR / "uploads"
DOCUMENT_TYPES_PATH = ROOT_DIR / "docs" / "documenttypes.md"

SENTRY_DSN = os.environ.get("SENTRY_DSN", "")
if SENTRY_DSN:
    import sentry_sdk
    sentry_sdk.init(dsn=SENTRY_DSN, traces_sample_rate=0.1)

# ─── Rate Limiting ────────────────────────────────────────────────────────────
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    limiter = Limiter(key_func=get_remote_address)
    _slowapi_available = True
except ImportError:
    limiter = None
    _slowapi_available = False

# ─── Prometheus ────────────────────────────────────────────────────────────────
try:
    from prometheus_fastapi_instrumentator import MetricsInstrumentator
    _prometheus_available = True
except ImportError:
    _prometheus_available = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    init_db(SCHEMA_PATH)
    if _prometheus_available:
        MetricsInstrumentator().instrument(app).expose(app)
    yield


api_key_header = APIKeyHeader(name="x-api-key", auto_error=False)

def get_api_key(api_key: str = Security(api_key_header)):
    expected = os.environ.get("CREDEXA_API_KEY")
    if expected and not secrets.compare_digest(api_key, expected):
        raise HTTPException(status_code=403, detail="Could not validate API Key")
    return api_key

app = FastAPI(title="Credexa AI - API", lifespan=lifespan, dependencies=[Depends(get_api_key)])

if _slowapi_available and limiter is not None:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    # Apply global rate limit per route via ASGI middleware is cleaner.
    # For simplicity, we attach limiter to app for per-route use.
    app.limiter = limiter

# CORS: restrict origins in production; allow localhost for dev
allow_origins = os.environ.get("CORS_ORIGINS", "http://localhost:5173,file://").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(mock_gov_router)


# ─── Health ───────────────────────────────────────────────────────────────────

@app.get("/health")
def health() -> dict:
    return {"status": "ok"}

@app.get("/healthz")
def healthz() -> dict:
    """Kubernetes-style liveness probe."""
    return {"status": "alive"}

@app.get("/ready")
def ready() -> dict:
    """Readiness probe: checks DB and model connectivity."""
    issues = []
    try:
        with get_db_connection() as conn:
            conn.cursor().execute("SELECT 1")
    except Exception as e:
        issues.append(f"database: {e}")
    model_dir = Path(__file__).resolve().parent.parent.parent / "models" / "trained"
    checks = {
        "anomaly_models": (model_dir / "anomaly" / "isolation_forest.pkl").exists(),
        "efficientnet": (model_dir / "efficientnet_b4_tamper" / "efficientnet_b4_tamper.pth").exists(),
    }
    for name, ok in checks.items():
        if not ok:
            issues.append(f"model:{name}")
    return {
        "status": "ready" if not issues else "degraded",
        "issues": issues,
        "checks": checks,
    }


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


# ─── Admin ─────────────────────────────────────────────────────────────────────

@app.post("/admin/retrain")
def retrain_anomaly_models():
    from anomaly.retrain import retrain_model
    result = retrain_model()
    if result is None:
        raise HTTPException(status_code=400, detail="Retraining failed — insufficient data or error")
    return {"status": "retrained", "path": result}

@app.post("/upload")
async def upload_documents(
    applicant_name: str = Form(...),
    application_type: str = Form(...),
    application_subtype: str = Form(""),
    mobile_no: str = Form(""),
    address: str = Form(""),
    files: List[UploadFile] = File(...),
):
    # Validate mobile_no if provided
    if mobile_no and not re.match(r"^\+?\d{10,15}$", mobile_no):
        raise HTTPException(status_code=400, detail="Invalid mobile number format")
    
    # Validate address length
    if address and len(address) > 500:
        raise HTTPException(status_code=400, detail="Address too long (max 500 chars)")
    
    # Validate applicant_name length
    if len(applicant_name) > 200:
        raise HTTPException(status_code=400, detail="Applicant name too long (max 200 chars)")

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
                "INSERT INTO cases (id, applicant_name, mobile_no, address, application_type, application_subtype, status, risk_score, submitted_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (case_id, applicant_name, encrypt_string(mobile_no), encrypt_string(address), application_type, application_subtype, "pending", 0, datetime.now(timezone.utc)),
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
    return {"case_id": case_id, "status": "pending", "files": saved_files}


# ─── Cases ────────────────────────────────────────────────────────────────────

@app.get("/cases")
def get_cases() -> dict:
    with get_db_connection() as conn:
        conn.autocommit = True
        with _cursor(conn) as cur:
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
        with _cursor(conn) as cur:
            cur.execute("SELECT * FROM cases WHERE id = %s", (case_id,))
            case = cur.fetchone()
            if not case:
                raise HTTPException(status_code=404, detail="Case not found")

            case_dict = dict(case)
            case_dict["mobile_no"] = decrypt_string(case_dict.get("mobile_no", ""))
            case_dict["address"] = decrypt_string(case_dict.get("address", ""))

            cur.execute("SELECT * FROM documents WHERE case_id = %s", (case_id,))
            documents = cur.fetchall()

            cur.execute("SELECT * FROM flags WHERE case_id = %s", (case_id,))
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
    with get_db_connection() as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM cases WHERE id = %s", (case_id,))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Case not found")
    process_case_task.delay(case_id)
    return {"status": "enqueued", "case_id": case_id}

class FeedbackIn(BaseModel):
    decision: str
    reviewer_id: str
    notes: str = ""

    @field_validator("decision")
    @classmethod
    def validate_decision(cls, v):
        if v.lower() not in FEEDBACK_DECISIONS:
            raise ValueError(f"decision must be one of {FEEDBACK_DECISIONS}")
        return v.lower()

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
            if feedback.decision in FEEDBACK_DECISIONS:
                cur.execute("UPDATE cases SET status = %s WHERE id = %s", (feedback.decision, case_id))
            return {"status": "success", "feedback_id": inserted_id}

@app.get("/cases/{case_id}/feedback")
def get_feedback(case_id: str) -> dict:
    with get_db_connection() as conn:
        conn.autocommit = True
        with _cursor(conn) as cur:
            cur.execute("SELECT * FROM feedback WHERE case_id = %s ORDER BY created_at DESC", (case_id,))
            feedbacks = cur.fetchall()
            return {"feedback": [dict(f) for f in feedbacks]}

@app.get("/cases/{case_id}/report")
def get_case_report(case_id: str) -> dict:
    from scoring.main import score_case
    from scoring.explainability import generate_explanation

    with get_db_connection() as conn:
        with _cursor(conn) as cur:
            cur.execute("SELECT * FROM cases WHERE id = %s", (case_id,))
            case = cur.fetchone()
            if not case:
                raise HTTPException(status_code=404, detail="Case not found")

            cur.execute("SELECT * FROM documents WHERE case_id = %s", (case_id,))
            documents = [dict(d) for d in cur.fetchall()]

            cur.execute("SELECT * FROM flags WHERE case_id = %s", (case_id,))
            flags = [dict(f) for f in cur.fetchall()]

            cur.execute("SELECT * FROM audit_log WHERE case_id = %s ORDER BY created_at ASC", (case_id,))
            audit_log = [dict(a) for a in cur.fetchall()]

    case_dict = dict(case)
    case_dict["mobile_no"] = decrypt_string(case_dict.get("mobile_no", ""))
    case_dict["address"] = decrypt_string(case_dict.get("address", ""))

    anomaly_score = case_dict.get("risk_score", 0) or 0
    scoring_result = score_case(flags, float(anomaly_score), case_id=case_id)

    doc_summaries = []
    for doc in documents:
        doc_flags = [f for f in flags if f.get("document_id") == doc["id"]]
        severity_order = {"high": 0, "medium": 1, "low": 2}
        doc_flags.sort(key=lambda x: severity_order.get(x.get("severity", "low"), 3))
        doc_summaries.append({
            "id": doc["id"],
            "file_name": doc["file_name"],
            "file_size": doc["file_size"],
            "doc_category": doc.get("doc_category", "Unknown"),
            "status": doc.get("status", "unknown"),
            "flag_count": len(doc_flags),
            "flags": doc_flags,
            "max_severity": max((f.get("severity", "low") for f in doc_flags), default="none"),
        })

    layers = {}
    for flag in flags:
        layer = flag.get("layer", "Other")
        layers.setdefault(layer, {"count": 0, "flags": []})
        layers[layer]["count"] += 1
        layers[layer]["flags"].append(flag)

    severity_counts = {"high": 0, "medium": 0, "low": 0}
    for flag in flags:
        sev = flag.get("severity", "low")
        if sev in severity_counts:
            severity_counts[sev] += 1

    return {
        "case": case_dict,
        "risk_score": scoring_result["risk_score"],
        "status": scoring_result["status"],
        "explanation": scoring_result["explanation"],
        "documents": doc_summaries,
        "layers": layers,
        "severity_counts": severity_counts,
        "flag_count": len(flags),
        "audit_log": audit_log,
    }
