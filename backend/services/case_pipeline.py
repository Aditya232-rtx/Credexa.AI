from __future__ import annotations

import os
import uuid
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Sequence

import psycopg2
from psycopg2.extras import RealDictCursor

from anomaly.main import detect_anomalies
from consistency.cross_doc import cross_check_documents, extract_entities
from forensics.file_forensics import inspect_office_file, inspect_pdf
from forensics.math_validator import validate_bank_statement_xlsx, validate_financials
from forensics.visual_forensics import run_ela
from ingestion.loader import read_document
from router.classifier import DocumentRouter
from scoring.main import score_case
import tempfile
from utils.encryption import decrypt_data
from db.connection import get_db_connection


class CasePipeline:
    def __init__(self, base_dir: Path, db_path: str, documenttypes_path: Path):
        self.base_dir = base_dir
        self.db_dsn = db_path  # We repurpose db_path as the DSN string
        self.documenttypes_path = documenttypes_path
        self.router = DocumentRouter(documenttypes_path=documenttypes_path)

    def _connect(self):
        return get_db_connection()

    def _insert_flag(self, cur, document_id: str | None, flag: Dict[str, Any]) -> None:
        cur.execute(
            "INSERT INTO flags (id, document_id, layer, finding, severity, score) VALUES (%s, %s, %s, %s, %s, %s)",
            (
                str(uuid.uuid4()),
                document_id,
                flag.get("layer", "Analysis"),
                flag.get("finding", ""),
                flag.get("severity", "low"),
                int(flag.get("score", 0)),
            ),
        )

    def process_case(self, case_id: str) -> Dict[str, Any]:
        with self._connect() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM cases WHERE id = %s", (case_id,))
                case = cur.fetchone()
                if not case:
                    raise ValueError(f"Case not found: {case_id}")

                cur.execute("SELECT * FROM documents WHERE case_id = %s ORDER BY file_name", (case_id,))
                documents = cur.fetchall()
                document_results: List[Dict[str, Any]] = []
                doc_entities: List[Dict[str, Any]] = []
                all_flags: List[Dict[str, Any]] = []

                cur.execute("UPDATE cases SET status = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s", ("processing", case_id))
                cur.execute("DELETE FROM flags WHERE document_id IN (SELECT id FROM documents WHERE case_id = %s)", (case_id,))
                cur.execute("DELETE FROM flags WHERE document_id IS NULL AND layer IN ('Cross-Doc Consistency', 'ML Anomaly')")

                for document in documents:
                    encrypted_file_path = self.base_dir / "uploads" / case_id / f"{document['id']}.enc"
                    
                    if not encrypted_file_path.exists():
                        continue
                        
                    file_path = None
                    try:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=(document["file_type"] or "")) as temp_file:
                            encrypted_content = encrypted_file_path.read_bytes()
                            temp_file.write(decrypt_data(encrypted_content))
                            temp_file.flush()
                            file_path = Path(temp_file.name)

                        payload = read_document(file_path)
                        payload["document_id"] = document["id"]
                        payload["file_size"] = int(document["file_size"] or 0)

                        category = self.router.classify_document(payload)
                        text = payload.get("text", "") or ""
                        tables = payload.get("tables", []) or []
                        metadata = payload.get("metadata", {}) or {}
                        pages = payload.get("pages", []) or []

                        flags: List[Dict[str, Any]] = []
                        file_type = (document["file_type"] or "").lower()
                        if file_type == ".pdf":
                            flags.extend(inspect_pdf(str(file_path), metadata))
                        else:
                            flags.extend(inspect_office_file(str(file_path), metadata))

                        if pages:
                            for index, page in enumerate(pages):
                                image_path = page.get("image_path")
                                if image_path and os.path.exists(image_path):
                                    flags.extend(run_ela(str(image_path)))
                                    try:
                                        os.remove(image_path)
                                    except Exception:
                                        pass

                        if file_type == ".xlsx" or file_type == ".csv" or file_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
                            try:
                                import openpyxl

                                workbook = openpyxl.load_workbook(file_path, data_only=False)
                                workbook_data = openpyxl.load_workbook(file_path, data_only=True)
                                sheets_data: Dict[str, Any] = {}
                                for sheet_name in workbook.sheetnames:
                                    sheet = workbook[sheet_name]
                                    data_sheet = workbook_data[sheet_name]
                                    sheet_rows: List[List[Dict[str, Any]]] = []
                                    for row_index, row in enumerate(sheet.iter_rows()):
                                        row_data: List[Dict[str, Any]] = []
                                        for col_index, cell in enumerate(row):
                                            value_cell = data_sheet.cell(row=row_index + 1, column=col_index + 1)
                                            if cell.value is None and value_cell.value is None:
                                                continue
                                            row_data.append(
                                                {
                                                    "coordinate": cell.coordinate,
                                                    "formula": cell.value if cell.data_type == "f" else None,
                                                    "value": value_cell.value,
                                                    "hyperlink": cell.hyperlink.target if cell.hyperlink else None,
                                                }
                                            )
                                        if row_data:
                                            sheet_rows.append(row_data)
                                    sheets_data[sheet_name] = {"hidden": sheet.sheet_state == "hidden", "rows": sheet_rows}
                                flags.extend(validate_bank_statement_xlsx(sheets_data))
                            except Exception:
                                pass

                        if file_type == ".xlsx" or any(token in text.lower() for token in ["balance sheet", "profit", "loss", "reconciliation", "bank statement"]):
                            flags.extend(validate_financials(text, tables, file_type))

                        entities = extract_entities(text)
                        doc_entities.append({"doc_id": document["id"], "entities": entities})

                        for flag in flags:
                            self._insert_flag(cur, document["id"], flag)

                        document_results.append(
                            {
                                "document_id": document["id"],
                                "file_name": document["file_name"],
                                "category": category,
                                "flags": flags,
                                "entities": entities,
                                "text_preview": text[:500],
                            }
                        )
                        all_flags.extend(flags)
                    finally:
                        if file_path and file_path.exists():
                            file_path.unlink()

                cross_doc_flags = cross_check_documents(doc_entities)
                for flag in cross_doc_flags:
                    self._insert_flag(cur, None, flag)
                all_flags.extend(cross_doc_flags)

                anomaly_result = detect_anomalies(document_results)
                for flag in anomaly_result.flags:
                    self._insert_flag(cur, None, flag)
                all_flags.extend(anomaly_result.flags)

                scoring = score_case(all_flags, anomaly_result.score)
                cur.execute(
                    "UPDATE cases SET status = %s, risk_score = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                    (scoring["status"], scoring["risk_score"], case_id),
                )
                cur.execute(
                    "INSERT INTO audit_log (id, case_id, action, details) VALUES (%s, %s, %s, %s)",
                    (str(uuid.uuid4()), case_id, "analysis_completed", scoring["explanation"]),
                )
            conn.commit()

            return {
                "case_id": case_id,
                "risk_score": scoring["risk_score"],
                "status": scoring["status"],
                "explanation": scoring["explanation"],
                "documents": document_results,
                "flags": all_flags,
            }

