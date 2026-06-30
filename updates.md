# Credexa.AI — Status Report (v1)

## ✅ What's Done (Model Integrations Complete)

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

### New Model Integrations (v1.1)
| Model | Category | Integration Point | Status |
|-------|----------|------------------|--------|
| `VK1402/AADHAAR_Extractor` (GLiNER2) | Indian PII extraction | `backend/ner/indian_pii.py` — Person Name, PAN, Aadhaar, IFSC, Bank Name via neural NER with regex fallback | ✅ |
| `Bombek1/ai-image-detector-siglip-dinov2` | Deepfake/AI image detection | `backend/models/bombek1_detector.py` — SigLIP2 + DINOv2 ensemble covering DALL-E 3, Midjourney V6, Flux, SD XL, 25+ generators (0.9997 AUC) | ✅ |
| Phonetic transliteration (`text-unidecode`) | Indic name matching | `backend/consistency/cross_doc.py` — `_phonetic_score()` for Devanagari/Indic script name normalization | ✅ |

### Improved Pipeline Layers
| Layer | Before | After |
|-------|--------|-------|
| Cross-Doc NER | spaCy only (misses Indian PII: PAN, Aadhaar, IFSC) | spaCy + GLiNER2 (VK1402/AADHAAR_Extractor) + regex patterns for Indian documents |
| Visual Forensics | CNNDetection (ResNet-50, GAN-only, weights missing) | Bombek1 SigLIP2+DINOv2 ensemble (covers diffusion models, 0.9997 AUC, auto-downloaded from HF) |
| Name Matching | Semantic (MiniLM) + fuzzy only | + Phonetic transliteration (`text-unidecode`) for Devanagari/Indic scripts |

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

### Model Download (Automatic on First Run)
4. `Bombek1/ai-image-detector-siglip-dinov2` checkpoint (2.11 GB) auto-downloads via `huggingface_hub` on first `run_bombek1_inference()` call to `models/trained/bombek1_ai_detector/pytorch_model.pt`
5. `VK1402/AADHAAR_Extractor` (GLiNER2, ~0.2B params) auto-downloads via `GLiNER.from_pretrained()` on first `extract_with_gliner()` call

### Packaging (User Action Required)
6. Configure `electron-builder` in `frontend/package.json`
7. Package for macOS/Linux/Windows

### End-to-End Verification (User Action Required)
8. Install new deps: `pip install gliner timm peft text-unidecode`
9. Start backend with `DB_BACKEND=sqlite` (no PostgreSQL dependency)
10. Start frontend (`npm run dev` or Electron)
11. Upload sample documents and verify pipeline runs to completion
12. Test with Docker Compose for PostgreSQL mode

---

## 🔧 What Needs Improvement

### Code Quality
| Area | Issue | Priority |
|------|-------|----------|
| `test_pipeline_e2e.py` | Root-level integration test expects PostgreSQL running — not part of `tests/` suite | Low |
| `check_services.py` | Standalone connectivity checker, not integrated | Low |
| `scripts/train/*.py` | Training scripts contain `sys.path.insert` — should use installed package | Low |
| `backend/mock_gov_apis/` | Mock APIs for testing — not production-ready | Low |
| `backend/ner/` | New NER module — needs tests | Low |
| `backend/models/bombek1_detector.py` | New AI detector module — needs tests | Low |

### Model Integration Remaining
| Model | Status | Priority |
|-------|--------|----------|
| EfficientNet-B4 tamper | Weights not trained — blocked on CASIA upload | Medium |
| Chitrapathak-2 (Indic OCR) | Researched but not integrated (4B VLM, heavy — needs vLLM/quantization) | Low |
| OpenBharatOCR (structured docs) | Researched but not integrated (pip-installable, needs YOLO weights) | Low |
| `hiteshwadhwani/pii-model-indicv2` | Alternative IndicBERTv2 PII — not integrated (GLiNER chosen instead) | Low |

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
| New deps | `gliner`, `timm`, `peft`, `text-unidecode` added to `requirements.txt` — need Dockerfile update | Low |
