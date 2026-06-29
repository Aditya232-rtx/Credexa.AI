# Credexa.AI — Changelog

## Latest (all issues resolved)

### Core Fixes
- SQLite dual-backend support (`DB_BACKEND=sqlite` or `postgres`)
- Encryption now aborts on missing key (prevents silent data loss)
- Flag deletion scoped to `case_id` (was wiping all cases)
- API key comparison uses `secrets.compare_digest` (timing-safe)
- CORS restricted to `CORS_ORIGINS` env var
- Input validation for uploads (mobile, address, name)
- Feedback decisions moved to constants (`FEEDBACK_DECISIONS`)

### Pipeline
- Per-document execution timeout (`LAYER_TIMEOUT`, default 120s)
- `QuickScanPipeline` — lightweight mode (skip heavy ML) via `QUICK_SCAN=true`
- Temp file cleanup in try/finally
- XLSX MIME-to-extension mapping (was silently skipping validation)
- PRNU analysis and DCT ghost wired into pipeline
- Font inspection wired for PDFs

### Imports & Dependencies
- Removed `sys.path.insert` hacks from tasks.py, api/main.py, test_pipeline_e2e.py
- `RealDictCursor` import made conditional on PostgreSQL
- Lazy imports for SentenceTransformer, spaCy, pandas, LayoutLMv3
- Removed unused deps: pytesseract, langchain, python-doctr

### Documentation
- Colab training notebook for EfficientNet-B4 on CASIA dataset
- Cross-doc Devanagari limitation noted
- Classifier Devanagari limitation noted
- Docker compose frontend node_modules cached via named volume

### Testing
- 132 pytest tests passing, 4 skipped (optional deps)
- `conftest.py` with backend PYTHONPATH setup
- Import tests moved to `tests/` as pytest-collectable

### Remaining
1. Train EfficientNet-B4: run `scripts/train/colab_train_visual_forensics.ipynb` on Colab T4
2. Download `efficientnet_b4_tamper.pth` → `models/trained/efficientnet_b4_tamper/`
3. Configure `electron-builder` for packaging
4. End-to-end verification with real uploads
