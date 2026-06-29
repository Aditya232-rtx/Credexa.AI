from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any, Dict, List, Sequence

from anomaly.main import detect_anomalies
from consistency.cross_doc import cross_check_documents, extract_entities
from forensics.file_forensics import inspect_office_file, inspect_pdf
from forensics.math_validator import validate_bank_statement_xlsx, validate_financials
from forensics.visual_forensics import run_ela
from ingestion.loader import read_document
from router.classifier import DocumentRouter
from scoring.main import score_case
from db.connection import get_db_connection


class QuickScanPipeline:
    """Lightweight pipeline for rapid testing — skips heavy ML (LayoutLM, EfficientNet, PRNU).

    Runs classification, OCR, math validation, cross-doc checks, and anomaly detection
    without loading deep learning models.
    """

    def __init__(self, base_dir: Path, db_path: str, documenttypes_path: Path):
        self.base_dir = base_dir
        self.db_dsn = db_path
        self.documenttypes_path = documenttypes_path
        self.router = DocumentRouter(documenttypes_path=documenttypes_path)

    def _connect(self):
        return get_db_connection()

    def _insert_flag(self, cur, case_id: str, document_id: str | None, flag: Dict[str, Any]) -> None:
        cur.execute(
            "INSERT INTO flags (id, case_id, document_id, layer, finding, severity, score) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (
                str(uuid.uuid4()),
                case_id,
                document_id,
                flag.get("layer", "Analysis"),
                flag.get("finding", ""),
                flag.get("severity", "low"),
                int(flag.get("score", 0)),
            ),
        )

    def process_case(self, case_id: str) -> Dict[str, Any]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM cases WHERE id = %s", (case_id,))
                case_row = cur.fetchone()
                if not case_row:
                    raise ValueError(f"Case {case_id} not found")
                case = dict(case_row) if isinstance(case_row, dict) else {"id": case_row[0]}

                cur.execute("UPDATE cases SET status = 'processing' WHERE id = %s", (case_id,))
                cur.execute("SELECT * FROM documents WHERE case_id = %s", (case_id,))
                document_rows = cur.fetchall()

        documents: List[Dict[str, Any]] = []
        for doc_row in document_rows:
            doc = dict(doc_row) if isinstance(doc_row, dict) else {}
            raw = self._read_document(doc.get("id", ""), doc)
            if raw:
                documents.append(raw)

        # Classify
        for d in documents:
            text = d.get("text", "") or ""
            metadata = d.get("metadata", {}) or {}
            classifications = self.router.classify(text, metadata)
            d["classification"] = classifications

        # Quick scan: math validation only (no heavy forensics)
        all_flags: List[Dict[str, Any]] = []
        for d in documents:
            file_type = d.get("file_type", "")
            file_ext = Path(d.get("file_name", "")).suffix.lower()
            text = d.get("text", "") or ""

            if file_ext == ".xlsx" or file_type in ("xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"):
                sheets = d.get("sheets", [])
                if sheets:
                    all_flags.extend(validate_bank_statement_xlsx(sheets))
                    all_flags.extend(validate_financials({"text": text, "tables": d.get("tables", [])}))
            elif file_ext in (".xls",) or file_type in ("xls", "application/vnd.ms-excel"):
                all_flags.extend(validate_financials({"text": text, "tables": d.get("tables", [])}))

        # Cross-doc consistency
        cross_doc_flags = cross_check_documents(documents)
        all_flags.extend(cross_doc_flags)

        # Anomaly detection (uses lightweight sklearn models only)
        for doc in documents:
            if "flags" not in doc:
                doc["flags"] = []
            doc["flags"].extend(all_flags)
        anomaly_result = detect_anomalies(documents)
        all_flags.extend(anomaly_result.flags)

        # Score
        risk_score = score_case(all_flags, anomaly_result.score)

        # Persist flags
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM flags WHERE case_id = %s", (case_id,))
                for flag in all_flags:
                    self._insert_flag(cur, case_id, None, flag)
                cur.execute(
                    "UPDATE cases SET status = %s, risk_score = %s WHERE id = %s",
                    (risk_score["status"], risk_score["risk_score"], case_id),
                )

        return {"case_id": case_id, "flags": all_flags, "risk_score": risk_score}

    def _read_document(self, doc_id: str, doc_row: Dict[str, Any]) -> Dict[str, Any] | None:
        file_name = doc_row.get("file_name", "")
        raw_data = doc_row.get("raw_data")
        if not raw_data:
            return None
        try:
            raw_bytes = bytes(raw_data) if not isinstance(raw_data, bytes) else raw_data
            result = read_document(raw_bytes, file_name)
            result["document_id"] = doc_id
            return result
        except Exception:
            return None
