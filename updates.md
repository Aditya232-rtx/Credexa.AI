# Credexa.AI — Status Report (v1)

## ✅ What's Done (47/47 Issues Resolved)

### Core Backend
- FastAPI application with 12 REST endpoints (health, upload, cases, analyze, feedback, report)
- Celery worker for async pipeline processing
- SQLite dual-backend support (`DB_BACKEND=sqlite|postgres`) with WAL mode
- Encryption at rest (Fernet) with abort-on-missing-key (prevents silent data loss)
- API key authentication with timing-safe comparison (`secrets.compare_digest`)
- CORS restricted to `CORS_ORIGINS` env var (default: localhost:5173, file://)
- Input validation for uploads (mobile regex, address ≤500, name ≤200)
- Rate limiting via slowapi
- Prometheus metrics instrumentation

### Analysis Pipeline
| Layer | Components | Status |
|-------|-----------|--------|
| Ingestion | OCR (RapidOCR, pdfplumber, PyMuPDF), Office reader (DOCX/XLSX/CSV), Image loader | ✅ |
| Routing | Keyword-based DocumentRouter with LayoutLMv3 as optional signal | ✅ |
| File Forensics | PDF layer/font inspection, Office metadata extraction | ✅ |
| Visual Forensics | ELA, DCT ghost, PRNU noise fingerprinting | ✅ |
| Math Validation | Bank statement XLSX validation, financial ratio cross-check | ✅ |
| Cross-Doc | NER entity extraction, fuzzy matching, ITR vs 26AS reconciliation | ✅ |
| ML Anomaly | Isolation Forest, ECOD, Autoencoder ensemble | ✅ |
| Explainability | Ollama LLM prompt with sanitized case_id | ✅ |

### Scoring & Decisions
- 4-tier risk score (clear: 0-20, review: 21-50, flagged: 51-80, critical: 81-100)
- LLM-generated underwriter explanation
- Feedback system (approved/rejected with reviewer notes)

### Frontend
- React 18 + Vite + Tailwind CSS + Zustand state management
- Views: Dashboard, CaseDetail, Upload (with drag-drop), Reports
- Components: RiskGauge, FlagCard, DocumentCard, Sidebar, Toast
- Electron IPC bridge for native file dialog (readFile via contextBridge)
- `.docx` MIME type fixed

### Database
- `cases` table with encrypted PII (mobile, address)
- `documents`, `flags` (scoped to `case_id`), `feedback`, `audit_log` tables
- Schema: SQLite (`schema_sqlite.sql`) + PostgreSQL (`schema.sql`)

### Testing
- 132 pytest tests passing (4 skipped for optional deps)
- Tests cover: anomaly, cross-doc, explainability, file forensics, imports, integration, ITR/26AS, math validator, ML baselines, pattern detector, retrain, scoring, visual forensics
- `conftest.py` with backend PYTHONPATH setup
- `test_imports_collectable.py` for CI import verification

### DevOps
- Docker Compose (db + redis + ollama + backend + celery + frontend)
- Dockerfile with system deps (tesseract, exiftool, poppler)
- `.dockerignore` to exclude venv, .env, node_modules
- GitHub Actions CI (postgres, redis, pytest + coverage)
- Git LFS tracking for model/data files

### Colab Training
- `colab_train_visual_forensics.ipynb` — EfficientNet-B4 on CASIA (75 epochs, T4 GPU)
- `data/casia_combined/` — 14,281 images (8237 Au + 6044 Tp), pre-split
- `data/casia_combined.zip` — 2.6GB archive

---

## 🔲 What's Pending

### Model Training (User Action Required)
1. Upload `data/casia_combined.zip` (2.6 GB) to Google Colab via Google Drive or direct upload
   - ⚠️ Zip exceeds GitHub's 2 GB LFS limit — not stored in repo
   - Host it on Google Drive, then mount Drive in Colab
2. Run `scripts/train/colab_train_visual_forensics.ipynb` on T4 GPU (~45-75 min)
3. Download `efficientnet_b4_tamper.pth` into `models/trained/efficientnet_b4_tamper/`

### Packaging (User Action Required)
4. Configure `electron-builder` in `frontend/package.json`
5. Package for macOS/Linux/Windows

### End-to-End Verification (User Action Required)
6. Start backend with `DB_BACKEND=sqlite` (no PostgreSQL dependency)
7. Start frontend (`npm run dev` or Electron)
8. Upload sample documents and verify pipeline runs to completion
9. Test with Docker Compose for PostgreSQL mode

---

## 🔧 What Needs Improvement

### Code Quality
| Area | Issue | Priority |
|------|-------|----------|
| `test_pipeline_e2e.py` | Root-level integration test expects PostgreSQL running — not part of `tests/` suite | Low |
| `check_services.py` | Standalone connectivity checker, not integrated | Low |
| `scripts/train/*.py` | Training scripts contain `sys.path.insert` — should use installed package | Low |
| `backend/mock_gov_apis/` | Mock APIs for testing — not production-ready | Low |

### Missing Features & Edge Cases
| Feature | Details | Priority |
|---------|---------|----------|
| WebSocket progress | No real-time pipeline progress for the frontend | Medium |
| Batch upload | Only single-case upload supported | Low |
| Export report | No PDF/CSV export of case reports | Low |
| User auth | No user login/multi-tenancy (single-user desktop app) | Low |
| Migration script | No script to migrate SQLite → PostgreSQL | Low |
| Model versioning | No model registry for trained weights | Low |

### Documentation
| Doc | Status | Priority |
|-----|--------|----------|
| `README.md` | Updated with pipeline overview | Good |
| `updates.md` | This file — current | Good |
| API reference | No generated OpenAPI/Swagger docs linked | Low |
| Deployment guide | No production deployment instructions | Medium |

### Infrastructure
| Area | Status | Priority |
|------|--------|----------|
| `.env` file | Contains real ENCRYPTION_KEY — `.gitignore` prevents committing | Good |
| Docker Compose | Frontend rebuilds node_modules on container restart (named volume caches it) | Low |
| CI pipeline | Runs pytest on push/PR to main/develop — needs model artifact caching | Low |
| Sentry/error tracking | Configured via `SENTRY_DSN` env var — not active in dev | Low |
