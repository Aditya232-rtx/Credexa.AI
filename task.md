# Credexa Gap Analysis Remediation Tasks

## Critical Bugs
- `[ ]` **Model Name & Env Var**: Update `math_validator.py` to use `OLLAMA_MODEL` environment variable (default `qwen3.5:4b`).
- `[ ]` **Encryption Key Persistence**: Update `utils/encryption.py` to load strictly from `.env` and abort if missing on existing instances.
- `[ ]` **Environment Template**: Create `.env.example` with keys.
- `[ ]` **Document Types Path**: Fix path in `tasks.py` to `docs/documenttypes.md`.
- `[ ]` **Feedback Endpoints**: Add `POST` and `GET` `/cases/{case_id}/feedback` in `api/main.py`.

## Infrastructure & Quality
- `[ ]` **Dockerize Ollama**: Add `ollama` service to `docker-compose.yml` and point `OLLAMA_URL` accordingly.
- `[ ]` **Offline Model Downloader**: Create `scripts/download_models.py` for LayoutLMv3 and MiniLM.
- `[ ]` **API Authentication**: Add `x-api-key` validation to FastAPI endpoints.
- `[ ]` **Structured Logging**: Replace `print()` with `loguru` in `api/main.py`, `celery_app.py`, and `tasks.py`.
- `[ ]` **ONNX Optimization**: Wire up `onnxruntime` inference in `ocr.py`.
- `[ ]` **Automated Tests**: Create pytest suite (`test_math_validator.py`, `test_scoring.py`, `test_cross_doc.py`) and `.github/workflows/python-ci.yml`.

## Missing Features (Fraud Detection & Forensics)
- `[ ]` **Explainability Engine**: Create `scoring/explainability.py` to prompt Ollama for risk reasoning and wire it into `scoring/main.py`.
- `[ ]` **Anomaly Domain Features**: Expand Isolation Forest vector in `anomaly/main.py` (round numbers, standard devs, confidence).
- `[ ]` **Pattern Detector**: Build `anomaly/pattern_detector.py` for monetary anomalies and sequences.
- `[ ]` **Feedback Retraining**: Build `anomaly/retrain.py` to retrain Isolation Forest from the feedback table.
- `[ ]` **ITR vs 26AS Check**: Add income reconciliation in `forensics/math_validator.py`.
- `[ ]` **Font Stream Forensics**: Implement font consistency checking in `forensics/file_forensics.py`.
- `[ ]` **Cross-Doc Advanced Validation**: Add address fuzzy-matching and income vs salary credits check in `consistency/cross_doc.py`.
- `[ ]` **PRNU Fingerprinting**: Build camera sensor fingerprinting in `forensics/prnu_check.py`.
- `[ ]` **DCT Ghost Analysis**: Implement double-compression detection in `forensics/visual_forensics.py`.
