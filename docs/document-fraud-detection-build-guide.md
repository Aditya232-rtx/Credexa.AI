# Credexa AI — Document Fraud Detection for Loan Underwriting
### Build Guide & Implementation Plan (Electron Desktop)

## Problem Statement
"Real-time anomaly detection
How can a bank automatically detect tampering or changes or forgery attempts made across land records, legal documents and financial statements in real time and provide intelligent insights to support faster, reliable decision-making during underwriting."

This guide maps every block in the production architecture diagram to a concrete open-source tool, a prototype-scale implementation note, and reference links. Scope is hackathon/prototype level: local models, mocked government APIs, single-machine deployment — but each module is swappable for a production equivalent without changing the pipeline shape.

---

## ∆ What Changed: Web App → Electron Desktop

| Concern | Original (Web) | Updated (Electron Desktop) |
|---|---|---|
| **UI Layer** | Streamlit or Next.js served in browser | Electron 30+ wrapping React 18 + Vite in Chromium |
| **Python Backend** | FastAPI server, public-facing | FastAPI spawned as a child subprocess, `127.0.0.1:8765` only |
| **File Access** | Browser File API / multipart HTTP upload | `electron.dialog.showOpenDialog` → local file path passed to Python; supports PDF, images, DOCX, XLSX, CSV |
| **Database** | PostgreSQL or SQLite on server | SQLite at `app.getPath('userData')` → `~/Library/Application Support/Credexa AI/credexa.db` |
| **Distribution** | Docker / cloud deploy | `.app` bundle via `electron-builder` — drag to `/Applications` |
| **Process model** | Long-running web server | Main process (Electron/Node) + Renderer (React) + Python subprocess |
| **Network** | Open port on server | Loopback-only. Nothing leaves the machine. |

**What stays identical:** Every Python pipeline module — OCR, metadata forensics, visual forensics, math validator, NER cross-doc consistency, ML anomaly engine, score aggregator, explainability — is untouched. The FastAPI routes don't change. SQLite schema doesn't change. Only how the app is _packaged and launched_ changes.

---

## 1. System Recap

```
Upload → OCR + Metadata → Doc Type Router (LayoutLMv3)
   ├── Financial Bucket  → Native PDF / DOCX / XLSX / CSV path → Metadata+Font / ELA+Texture → Math Validator → TRACES/CBDT check
   ├── Legal Bucket      → Document Photo / Raster path → PRNU / DCT+GAN check
   └── Land+Identity     → Identity Document path       → PRNU+DCT+Govt Source API
            ↓
   Detection Aggregator
            ↓
   Cross-Doc Consistency Engine  +  External Ground Truth
            ↓
   ML Anomaly Engine (Isolation Forest, NLP Extractor, Pattern Detector)
            ↓
   Score Aggregator → Explainability Engine (LLM)
            ↓
   Underwriter Dashboard / Case Management / Audit Log → Feedback Loop
```

---

## ∆ Updated Architecture

```
Electron Main Process (Node.js)
  ├── Spawns Python subprocess → FastAPI on localhost:8765 (loopback only)
  ├── Handles native OS events (file dialog, app lifecycle, tray)
  └── Creates BrowserWindow → loads React renderer

React Renderer (Chromium, localhost:5173 in dev / dist/index.html in prod)
  └── Makes HTTP calls to localhost:8765 (Python FastAPI)

Python FastAPI (localhost:8765)
  ├── /upload        → ingestion → routing → forensics → scoring
  ├── /cases         → SQLite read
  ├── /explain/{id}  → Ollama/Qwen explainability
  └── /mock-gov/*    → mocked TRACES / MCA21 / AA / Bhulekh endpoints

SQLite (~/Library/Application Support/Credexa AI/credexa.db)
  └── tables: cases, documents, flags, audit_log, feedback
```

---

## ∆ Updated Repo Structure

```
credexa-desktop/
│
├── electron/
│   ├── main.js                  # BrowserWindow + Python subprocess spawn
│   └── preload.js               # contextBridge — exposes safe IPC to renderer
│
├── frontend/                    # Vite + React 18 + Tailwind
│   ├── src/
│   │   ├── App.jsx
│   │   ├── views/
│   │   │   ├── Dashboard.jsx
│   │   │   ├── CaseDetail.jsx
│   │   │   └── Upload.jsx
│   │   └── components/
│   │       ├── RiskGauge.jsx
│   │       ├── FlagCard.jsx
│   │       └── Sidebar.jsx
│   ├── tailwind.config.js
│   └── vite.config.js
│
├── backend/                      # Python backend (all pipeline modules)
│   ├── api/
│   │   └── main.py              # FastAPI orchestration (unchanged)
│   ├── ingestion/
│   │   ├── ocr.py
│   │   ├── metadata.py
│   │   └── office_reader.py     # DOCX / XLSX / CSV extraction
│   ├── router/
│   │   └── classifier.py
│   ├── forensics/
│   │   ├── file_forensics.py
│   │   ├── visual_forensics.py
│   │   └── math_validator.py
│   ├── consistency/
│   │   └── cross_doc.py
│   ├── mock_gov_apis/
│   │   └── main.py
│   ├── anomaly/
│   │   ├── isolation_forest.py
│   │   ├── nlp_extractor.py
│   │   └── pattern_detector.py
│   ├── scoring/
│   │   ├── aggregator.py
│   │   └── explainability.py
│   ├── db/
│   │   └── schema.sql
│   └── requirements.txt
│
├── assets/
│   └── icon.icns                # macOS app icon
│
├── package.json                 # Root — Electron scripts
└── .env
```

---

## 2. Component-by-Component Build Guide

### 2.1 Ingestion — OCR & Text Extraction

| Tool | Use | Link |
|---|---|---|
| pdfplumber | Native PDF text/table extraction | https://github.com/jsvine/pdfplumber |
| Tesseract OCR | OCR for scanned/image documents | https://github.com/tesseract-ocr/tesseract |
| PaddleOCR | Stronger OCR + layout detection, good for Indian scripts | https://github.com/PaddlePaddle/PaddleOCR |
| pytesseract | Python wrapper for Tesseract | https://github.com/madmaze/pytesseract |
| python-docx | Extract text, tables, and metadata from `.docx` files | https://python-docx.readthedocs.io/ |
| openpyxl | Read `.xlsx` spreadsheets — amounts, headers, cell formulas | https://openpyxl.readthedocs.io/ |
| pandas | Parse `.csv` files; normalize and reconcile tabular financial data | https://pandas.pydata.org/ |

**Implementation note:** Try pdfplumber first (native PDFs return clean text + bounding boxes). If text extraction returns empty/garbage → fall back to PaddleOCR/Tesseract on rasterized pages (PyMuPDF can rasterize a PDF page to image). For `.docx`, use `python-docx` to iterate paragraphs and tables directly — no OCR needed. For `.xlsx` / `.csv`, `openpyxl` + `pandas` give you structured DataFrames that feed directly into the Math Validator.

---

### 2.2 Metadata Capture

| Tool | Use | Link |
|---|---|---|
| ExifTool | Full metadata dump (creation tool, timestamps, edit history) | https://exiftool.org/ |
| PyMuPDF (fitz) | PDF-specific metadata, page rendering, XObject inspection | https://github.com/pymupdf/PyMuPDF |
| pikepdf (qpdf wrapper) | PDF structure/object inspection — detect overlay layers | https://github.com/pikepdf/pikepdf |
| python-docx | DOCX core properties: `author`, `last_modified_by`, `created`, `modified` | https://python-docx.readthedocs.io/ |
| openpyxl | XLSX workbook properties: creator, last modified by, revision count | https://openpyxl.readthedocs.io/ |

**Implementation note:** `exiftool -j file.pdf` gives JSON metadata in one call — flag if `Producer`/`Creator` looks inconsistent with the claimed document source (e.g. a "bank-issued" PDF whose Producer is `Microsoft Print to PDF` or edited in `Adobe Acrobat Pro` hours after the claimed issue date). For DOCX files, `document.core_properties.last_modified_by` differing from the claimed issuer is a strong signal. For XLSX, a non-zero `revision` count on a supposedly original statement warrants scrutiny. pikepdf can enumerate content streams to detect a text layer pasted over an image layer (classic whiting-out + retype).

---

### 2.3 Document Type Router / Classifier

| Tool | Use | Link |
|---|---|---|
| LayoutLMv3 (base) | Layout-aware document classification | https://huggingface.co/microsoft/layoutlmv3-base |
| Donut (Document Understanding Transformer) | OCR-free document classification/parsing | https://github.com/clovaai/donut |
| RVL-CDIP dataset | Pretraining/fine-tuning data for doc classification | https://www.cs.cmu.edu/~aharley/rvl-cdip/ |

**Implementation note:** For prototype speed, fine-tune LayoutLMv3-base on a small labeled set (bank statement / ITR / sale deed / Aadhaar / 7-12 extract / PoA / DOCX bank letter / XLSX financial statement, ~30–50 samples per class is enough for a demo-grade classifier). If time is tight, a zero-shot approach using the extracted OCR text + a prompt to a local LLM (Qwen2.5-7B via Ollama) for classification is a fast fallback. Route `.docx` and `.xlsx` files by MIME type before the ML classifier runs — they are almost always financial or legal documents and skip the OCR stage entirely.

---

### 2.4 File Forensics (PDF / DOCX layer / edit history)

| Tool | Use | Link |
|---|---|---|
| pikepdf | Inspect PDF object structure, content streams, layers | https://github.com/pikepdf/pikepdf |
| peepdf | PDF forensic analysis (suspicious objects, JS, structure) | https://github.com/jesparza/peepdf |
| ExifTool | Edit-history/timestamp anomalies across PDF, DOCX, XLSX | https://exiftool.org/ |
| Imago Forensics | Combined metadata + ELA + thumbnail forensic toolkit | https://github.com/redaelli/imago-forensics |
| python-docx | Detect tracked changes, revision history, embedded macros | https://python-docx.readthedocs.io/ |
| openpyxl | Detect formula tampering, hidden sheets, macro presence in XLSX | https://openpyxl.readthedocs.io/ |

**Implementation note:** Flag conditions for PDFs: multiple `/Type /XObject` overlapping bounding boxes on the same region, mismatched font subsets, or `ModifyDate` significantly later than `CreateDate` with a different `Producer`. For DOCX, inspect `word/document.xml` revision markup — unexplained tracked changes or a `w:rsidR` revision ID cluster inconsistency signals post-issue editing. For XLSX, hidden sheets (`sheet.sheet_state == 'hidden'`) or cells with `=HYPERLINK()` formulas pointing externally are red flags.

---

### 2.5 Visual / Image Forensics

| Tool | Use | Link |
|---|---|---|
| Pillow (ELA implementation) | Error Level Analysis — recompress at known quality, diff | https://pillow.readthedocs.io/ |
| Imago Forensics | Pre-built ELA + thumbnail + metadata pipeline | https://github.com/redaelli/imago-forensics |
| PRNU-Python | Sensor noise fingerprinting (camera-captured ID photos) | https://github.com/polimi-ispl/prnu-python |
| CNNDetection | Detect GAN-generated/manipulated image regions | https://github.com/peterwang512/CNNDetection |
| ManTraNet | End-to-end manipulation detection + localization | https://github.com/ISICV/ManTraNet |
| OpenCV | Texture analysis, DCT block analysis, font-edge consistency | https://github.com/opencv/opencv |

**Implementation note for ELA (quick build):** resave the image at JPEG quality 90, compute pixel-wise absolute difference with the original, amplify the difference map. Regions that were edited after the last save show up as bright blocks against a uniformly dark background. This is ~30 lines of Pillow/numpy and is the highest ROI forensic check for the time it takes to build.

For **DCT/double-compression analysis** (detects re-saved/edited JPEGs), the "JPEG Ghost" technique is well documented and implementable with numpy + OpenCV's DCT functions.

---

### 2.6 Logic / Mathematical Consistency (Math Validator)

No external library needed beyond what's already listed — this is pure business logic over the extracted fields.

| Check | Formula |
|---|---|
| Bank statement | `opening_balance + Σcredits − Σdebits == closing_balance` (per transaction line and overall) |
| Balance Sheet | `Assets == Liabilities + Equity` |
| P&L | `Gross Revenue − COGS − OpEx == Net Income` |
| ITR vs Form 26AS | declared income ≈ TDS-implied income within tolerance |

**Implementation note:** For PDFs, use `pandas` + `re`/regex to extract amount columns from OCR text. For `.xlsx` files, `openpyxl` gives direct cell access — compare formula-computed totals against stored cell values to detect manual overwrites. For `.csv`, `pandas` reads directly into a DataFrame ready for reconciliation. Normalize Indian number formats (lakhs/crores, commas) across all sources, then run reconciliation with a small tolerance band (e.g. ±1%) to allow for OCR rounding noise.

---

### 2.7 Cross-Document Consistency Engine

| Tool | Use | Link |
|---|---|---|
| RapidFuzz | Fast fuzzy string matching for names/addresses across docs | https://github.com/rapidfuzz/RapidFuzz |
| spaCy | Named entity extraction (names, dates, amounts, addresses) | https://spacy.io/ |
| dedupe | Entity resolution across records | https://github.com/dedupeio/dedupe |
| indic-nlp-library | Helps normalize Indian names/addresses (transliteration variants) | https://github.com/anoopkunchukuttan/indic_nlp_library |

**Implementation note:** Extract `{name, address, DOB/PAN, income, dates}` per document via spaCy NER + regex — works across PDF-extracted text, DOCX paragraphs, and XLSX cell values using the same extractor. Run RapidFuzz `token_sort_ratio` pairwise across documents. Below a similarity threshold (e.g. 85%) → flag as a cross-document inconsistency, surfaced with the two conflicting values side by side for the explainability engine.

---

### 2.8 External Ground Truth (mocked for prototype)

Real government APIs (TRACES, MCA21, Account Aggregator) require institutional access/MoUs and are **not directly callable** in a hackathon context — build a mock service layer with the same interface so it's a drop-in swap later.

| Real Source | Reference | Prototype Approach |
|---|---|---|
| Form 26AS / TRACES (TDS credits) | https://www.tdscpc.gov.in/ | Mock JSON endpoint returning sample TDS records |
| MCA21 (corporate filings) | https://www.mca.gov.in/ | Mock endpoint / scrape-able public search for demo company names |
| Account Aggregator framework | https://sahamati.org.in/ | Mock FI-data response in AA's published JSON schema |
| Maharashtra land records (7/12, Property Card) | https://bhulekh.mahabhumi.gov.in/ | Mock response keyed by survey number for demo |

**Implementation note:** Build a tiny FastAPI service `mock_gov_apis/` with endpoints `/traces/26as`, `/mca/company`, `/aa/fi-data`, `/bhulekh/712` returning canned JSON for a handful of demo identities — this lets the External Ground Truth block run end-to-end in the demo while making clear in your docs/pitch which calls become real integrations post-MoU.

---

### 2.9 ML Anomaly Engine

| Tool | Use | Link |
|---|---|---|
| scikit-learn (Isolation Forest) | Unsupervised outlier detection on numeric features | https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.IsolationForest.html |
| PyOD | Broader anomaly detection toolkit (multiple algorithms) | https://github.com/yzhao062/pyod |
| spaCy / Qwen2.5 (via Ollama) | NLP extractor — entities, semantic cross-checks | https://spacy.io/ , https://ollama.com/ |
| pandas | Pattern detector — round-number frequency, transaction sequence stats | https://pandas.pydata.org/ |

**Implementation note:** Feature set for Isolation Forest: transaction amount distribution stats (mean, std, % round numbers), balance volatility, income-to-credit ratio, date-gap irregularities, OCR-confidence scores per field. For XLSX bank statements, also include formula-vs-stored-value delta as a feature. Train on a set of "genuine" sample documents (synthetic is fine for demo) so the model has a baseline of "normal."

---

### 2.10 Score Aggregation + Explainability Engine

| Tool | Use | Link |
|---|---|---|
| Custom weighted scoring (Python) | Combine per-layer flags into 0–100 risk score | — |
| Ollama | Local LLM serving for explanation generation | https://ollama.com/ |
| Qwen2.5-7B-Instruct | Generates natural-language reasoning from structured flags | https://huggingface.co/Qwen/Qwen2.5-7B-Instruct |
| LangChain (optional) | Prompt templating / structured output parsing | https://github.com/langchain-ai/langchain |

**Implementation note:** Score aggregator = weighted sum across the 5 detection layers (weights tunable, start with equal weighting and adjust per layer's false-positive rate). Explainability engine takes the structured flag list (e.g. `{"font_mismatch": "page 3", "balance_reconciliation": "off by ₹14,200", "cross_doc_name_mismatch": "Aadhaar vs ITR", "xlsx_formula_overwrite": "cell D47"}`) and prompts the LLM with a fixed template. Keep the LLM out of the scoring decision itself — it only explains, the score is deterministic/auditable.

---

### 2.11 Output Layer — Electron Desktop

| Role | Tool | Notes |
|---|---|---|
| Desktop shell | Electron 30+ | Wraps Chromium + Node.js into a native `.app` bundle |
| Renderer UI | React 18 + Vite | Same dev experience as a web app — HMR, JSX, hooks |
| Styling | Tailwind CSS | Mapped to Credexa design tokens (Inter + JetBrains Mono) |
| Icons | lucide-react | All icons size 16, strokeWidth 1.8 |
| Bundler | electron-builder | Produces `.dmg` for distribution |
| Dev orchestration | concurrently + wait-on | Starts Vite dev server and Electron simultaneously |
| File picker | Electron dialog API | `dialog.showOpenDialog` — supports PDF, PNG, JPG, TIFF, DOCX, XLSX, CSV |
| Backend | FastAPI + Uvicorn | Child process on 127.0.0.1:8765 |
| Storage | SQLite | `app.getPath('userData')` — fully local, no cloud |

**electron/main.js** (core spawn logic):
```javascript
const { app, BrowserWindow, dialog, ipcMain } = require('electron');
const { spawn } = require('child_process');
const path = require('path');

let pythonProcess;
const isDev = !app.isPackaged;

function startPython() {
  const pythonRoot = isDev
    ? path.join(__dirname, '../python')
    : path.join(process.resourcesPath, 'python');

  pythonProcess = spawn('python3', [
    '-m', 'uvicorn', 'api.main:app',
    '--host', '127.0.0.1', '--port', '8765'
  ], { cwd: pythonRoot });

  pythonProcess.stderr.on('data', d => console.log('[Python]', d.toString()));
}

function createWindow() {
  const win = new BrowserWindow({
    width: 1280, height: 800,
    minWidth: 960, minHeight: 680,
    titleBarStyle: 'hiddenInset',   // native macOS traffic lights
    backgroundColor: '#FFFFFF',
    webPreferences: {
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    }
  });

  isDev
    ? win.loadURL('http://localhost:5173')
    : win.loadFile(path.join(__dirname, '../frontend/dist/index.html'));
}

// Expose file dialog to renderer securely via IPC
ipcMain.handle('open-file-dialog', async () => {
  const result = await dialog.showOpenDialog({
    properties: ['openFile', 'multiSelections'],
    filters: [{ name: 'Documents', extensions: ['pdf', 'png', 'jpg', 'jpeg', 'tiff', 'docx', 'xlsx', 'csv'] }]
  });
  return result.filePaths;
});

app.whenReady().then(() => {
  startPython();
  setTimeout(createWindow, 2000); // wait for FastAPI to be ready
});

app.on('will-quit', () => pythonProcess?.kill());
```

---

### 2.12 Feedback Loop

**Implementation note:** Log every reviewer decision (`approved` / `rejected` / `escalated`) against the document's feature vector. For the prototype, a periodic script that re-fits the Isolation Forest on the accumulated "approved = normal" samples demonstrates the loop without needing a full MLOps pipeline. Document this as the production hook for continuous retraining.

---

## 3. Datasets for Training / Testing

| Dataset | Use | Link |
|---|---|---|
| MIDV-2020 | Identity documents incl. forged/edited variants — test PRNU + DCT | https://github.com/SmartEngines/midv-2020 |
| CASIA v2 | Image splicing/copy-move ground truth — test ELA | https://github.com/namtpham/casia2groundtruth |
| FUNSD | Form understanding + layout/field extraction | https://guillaumejaume.github.io/FUNSD/ |
| RVL-CDIP | Document type classification (16 classes) — fine-tune LayoutLMv3 | https://www.cs.cmu.edu/~aharley/rvl-cdip/ |
| SROIE | Receipt OCR + key info extraction (proxy for financial docs) | https://rrc.cvc.uab.es/?ch=13 |
| DocBank | Document layout analysis pretraining | https://github.com/doc-analysis/DocBank |

For India-specific financial/legal document samples, generate **synthetic** bank statements, ITRs, and sale deeds using python-docx → DOCX and openpyxl → XLSX, then programmatically apply known tampering (edit a number, change a font, overwrite a formula result) to create labeled "forged" pairs for testing each forensic module.

---

## ∆ Updated Build Phases

| Phase | Deliverable | Change from original |
|---|---|---|
| **Phase 1** | Core pipeline skeleton: OCR + DOCX/XLSX/CSV reader → mock router → FastAPI returning stub JSON | Add `office_reader.py` alongside OCR |
| **Phase 2** | ELA, Math Validator, Metadata forensics | Add XLSX formula-vs-stored-value check |
| **Phase 3** | Cross-doc + scoring + mock govt APIs | No change |
| **Phase 4** | Isolation Forest + Ollama/Qwen explainability | No change |
| **Phase 5** | **Electron shell + React dashboard** | Replace Streamlit/Next.js with Electron + React renderer |
| **Stretch** | LayoutLMv3 classifier, PRNU/GAN forensics, `.dmg` packaging | Add `electron-builder` packaging step |

---

---

# Pre-Download Checklist
> Everything to install before writing a single line of Credexa code.
> Organized by layer. Commands are macOS-first.

---

## 1. System Prerequisites

| Tool | Why | Install |
|---|---|---|
| **Node.js 20 LTS** | Electron and all npm tooling | `brew install node@20` or https://nodejs.org |
| **nvm** (recommended) | Manage Node versions cleanly | `curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh \| bash` |
| **Python 3.11** | ML models and forensics libraries work best on 3.11 | `brew install python@3.11` |
| **pip** | Comes with Python | Verify: `python3.11 -m pip --version` |
| **Homebrew** | macOS package manager for system binaries | https://brew.sh |
| **Git** | Source control | `brew install git` |

---

## 2. Electron & Frontend (npm)

Install at the **project root** and inside `frontend/`:

### Root (Electron shell)
```bash
npm install --save-dev electron@latest
npm install --save-dev electron-builder
npm install --save-dev concurrently
npm install --save-dev wait-on
```

### frontend/ (React renderer)
```bash
npm create vite@latest frontend -- --template react
cd frontend
npm install
npm install lucide-react
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

| Package | Purpose |
|---|---|
| `electron` | Desktop shell |
| `electron-builder` | Produces `.dmg` / `.app` bundle with Python embedded |
| `concurrently` | Run Vite dev server + Electron simultaneously |
| `wait-on` | Hold Electron start until Vite is serving |
| `vite` + `@vitejs/plugin-react` | Fast React bundler |
| `react` + `react-dom` (v18) | UI framework |
| `tailwindcss` + `postcss` + `autoprefixer` | Utility CSS — mapped to Credexa design tokens |
| `lucide-react` | Icon set (size 16, strokeWidth 1.8 throughout) |

---

## 3. System Binaries (Homebrew)

```bash
# OCR engine + Indian language packs
brew install tesseract
brew install tesseract-lang   # includes Hindi, Marathi, Tamil, Telugu, Gujarati packs

# Metadata forensics
brew install exiftool
```

| Binary | Used in | Why system-level |
|---|---|---|
| `tesseract` | `pytesseract` Python wrapper | pytesseract calls the system binary |
| `tesseract-lang` | Indian script OCR on 7-12 extracts, Aadhaar, Patta | Trained `.traineddata` files needed at runtime |
| `exiftool` | `metadata.py` — PDF/DOCX/XLSX edit history, timestamp anomalies | CLI called via `subprocess` or `imago-forensics` |

---

## 4. Python — Core Backend

```bash
pip3.11 install fastapi "uvicorn[standard]" python-multipart pydantic
```

| Package | Purpose |
|---|---|
| `fastapi` | REST API framework — all pipeline endpoints |
| `uvicorn[standard]` | ASGI server that Electron spawns as subprocess |
| `python-multipart` | Enables `UploadFile` in FastAPI for document ingestion |
| `pydantic` | Data models and validation |

---

## 5. Python — OCR & Ingestion

```bash
pip3.11 install pdfplumber pytesseract PyMuPDF paddleocr paddlepaddle
```

| Package | Purpose |
|---|---|
| `pdfplumber` | Native PDF text + table extraction with bounding boxes |
| `pytesseract` | Python wrapper for system Tesseract binary |
| `PyMuPDF` (fitz) | PDF page rasterization, metadata, XObject inspection |
| `paddleocr` | Stronger OCR for Indian scripts and low-quality scans |
| `paddlepaddle` | PaddleOCR's required backend (CPU version) |

---

## 5a. Python — DOCX, XLSX & CSV Ingestion

```bash
pip3.11 install python-docx openpyxl pandas
```

| Package | Purpose |
|---|---|
| `python-docx` | Extract text, tables, paragraphs, and core properties from `.docx` files; detect tracked changes and revision metadata |
| `openpyxl` | Read `.xlsx` workbooks — cell values, formulas, sheet names, workbook properties (creator, revision count, last modified by) |
| `pandas` | Parse `.csv` files into DataFrames; normalize Indian number formats; feed directly into Math Validator reconciliation |

**Implementation note:** These three replace any need for OCR on office documents. `python-docx` iterates `document.paragraphs` and `document.tables` directly. `openpyxl` exposes both `cell.value` (stored value) and `cell.data_type` — comparing stored values against formula-implied totals detects manual overwrite tampering. `pandas.read_csv` handles BOM, encoding variants, and mixed delimiters common in exported bank statements.

---

## 6. Python — Metadata & File Forensics

```bash
pip3.11 install pikepdf Pillow opencv-python numpy imago-forensics
# peepdf is not on PyPI — install from source:
pip3.11 install git+https://github.com/jesparza/peepdf.git
```

| Package | Purpose |
|---|---|
| `pikepdf` | PDF object/content stream inspection — detect overlay layers, font mismatches |
| `Pillow` | Error Level Analysis (ELA) — ~30 lines, highest forensic ROI |
| `opencv-python` | DCT block analysis, JPEG ghost, texture analysis |
| `numpy` | Pixel math for ELA difference maps |
| `imago-forensics` | Pre-built ELA + thumbnail + metadata pipeline |
| `peepdf` | PDF structural forensics — detect JS injection, suspicious objects |

---

## 7. Python — Visual / Image Forensics

```bash
pip3.11 install prnu
# CNNDetection and ManTraNet — install from GitHub (no PyPI):
pip3.11 install git+https://github.com/peterwang512/CNNDetection.git
```

| Package | Purpose |
|---|---|
| `prnu` (prnu-python) | Sensor noise fingerprinting for camera-captured identity documents |
| `CNNDetection` | GAN-generated image region detection |
| `ManTraNet` | End-to-end image manipulation localization (stretch goal) |
| `opencv-python` | (also in §6) — DCT, PRNU, texture checks share this |

---

## 8. Python — NLP & Cross-Document Consistency

```bash
pip3.11 install spacy rapidfuzz dedupe indic-nlp-library
python3.11 -m spacy download en_core_web_sm
# Also download Hindi model for Aadhaar/regional doc NER:
python3.11 -m spacy download xx_ent_wiki_sm
```

| Package | Purpose |
|---|---|
| `spaCy` | Named entity extraction (names, DOB, PAN, addresses, amounts) across all docs including DOCX text |
| `en_core_web_sm` | spaCy English model — required at runtime |
| `xx_ent_wiki_sm` | Multilingual NER model — helps with Hindi/regional fields |
| `rapidfuzz` | Fast fuzzy string matching — pairwise name/address comparison across docs |
| `dedupe` | Entity resolution when the same person appears with spelling variations |
| `indic-nlp-library` | Normalizes Indian names and addresses (transliteration variants) |

---

## 9. Python — Math Validator

Uses packages already listed above:
- `pandas` (§5a) for amount column extraction and reconciliation from PDF-extracted text, DOCX tables, XLSX cells, and CSV rows
- `openpyxl` (§5a) for comparing XLSX formula-computed totals against stored cell values
- `re` (stdlib) for Indian number format normalization (lakhs, crores, commas)

---

## 10. Python — ML Anomaly Engine

```bash
pip3.11 install scikit-learn pyod pandas
```

| Package | Purpose |
|---|---|
| `scikit-learn` | Isolation Forest for unsupervised outlier detection on document features |
| `pyod` | Extended anomaly detection toolkit (LOF, ECOD, etc. — drop-in alternatives to IsolationForest) |
| `pandas` | Pattern detector — round-number frequency, transaction sequence stats, feature engineering |

---

## 11. Python — Explainability Engine

```bash
pip3.11 install langchain langchain-community requests
```

| Package | Purpose |
|---|---|
| `langchain` | Prompt templating and structured output parsing for Qwen |
| `langchain-community` | Ollama integration (`OllamaLLM` class) |
| `requests` | Direct HTTP fallback to Ollama API (`POST /api/generate`) |

---

## 12. AI Models — Download Before Starting

### Ollama (Local LLM runtime)
```bash
# 1. Install Ollama desktop app
#    → https://ollama.com/download  (drag to Applications)

# 2. Pull the Qwen model (one-time, ~4.7 GB for 7B Q4)
ollama pull qwen2.5:7b

# 3. Verify it works
ollama run qwen2.5:7b "Say hello"
```

### spaCy Models
```bash
python3.11 -m spacy download en_core_web_sm
python3.11 -m spacy download xx_ent_wiki_sm
```

### LayoutLMv3 (downloads automatically on first `classifier.py` run via HuggingFace)
```bash
pip3.11 install transformers datasets torch sentencepiece
# Model (~900MB) auto-downloads from: https://huggingface.co/microsoft/layoutlmv3-base
```

| Model | Size | When needed |
|---|---|---|
| `qwen2.5:7b` (via Ollama) | ~4.7 GB | Phase 4 — explainability engine |
| `layoutlmv3-base` (HuggingFace) | ~900 MB | Stretch — fine-tuned doc type classifier |
| `en_core_web_sm` (spaCy) | ~12 MB | Phase 3 — cross-doc NER |
| `xx_ent_wiki_sm` (spaCy) | ~50 MB | Phase 3 — multilingual NER |

---

## 13. Fonts (bundle into Electron app)

Download and add to `frontend/public/fonts/`:

| Font | Download | Used for |
|---|---|---|
| **Inter** (all weights: 400, 500, 600, 700) | https://fonts.google.com/specimen/Inter | All UI text, body, labels |
| **JetBrains Mono** (weights: 500, 600, 700) | https://www.jetbrains.com/lp/mono/ | Risk scores, case IDs, hashes, amounts |

Reference both in `frontend/src/index.css` using `@font-face` — don't rely on Google Fonts CDN in a desktop app (no internet dependency guarantee).

---

## 14. VS Code Extensions

Install all from the Extensions panel (`⌘⇧X`) or via CLI:

```bash
code --install-extension ms-python.python
code --install-extension ms-python.pylance
code --install-extension bradlc.vscode-tailwindcss
code --install-extension dbaeumer.vscode-eslint
code --install-extension esbenp.prettier-vscode
code --install-extension qwtel.sqlite-viewer
code --install-extension humao.rest-client
code --install-extension mechatroner.rainbow-csv
code --install-extension bierner.markdown-preview-github-styles
```

| Extension | Purpose |
|---|---|
| `ms-python.python` | Python language support, linting, venv detection |
| `ms-python.pylance` | Fast type checking and IntelliSense for the Python pipeline |
| `bradlc.vscode-tailwindcss` | Autocomplete for all Tailwind classes in JSX |
| `dbaeumer.vscode-eslint` | Lint React/JS in the frontend |
| `esbenp.prettier-vscode` | Format JS/JSX/JSON consistently |
| `qwtel.sqlite-viewer` | Inspect `credexa.db` audit log and cases directly in VS Code |
| `humao.rest-client` | Test FastAPI endpoints with `.http` files without leaving the editor |
| `mechatroner.rainbow-csv` | Visualize CSV bank statements and synthetic training datasets |
| `bierner.markdown-preview-github-styles` | Preview this build guide and your docs |

---

## 15. Optional but Recommended Desktop Tools

| Tool | Purpose | Get it |
|---|---|---|
| **TablePlus** or **DB Browser for SQLite** | GUI for inspecting the local SQLite audit log | https://tableplus.com / https://sqlitebrowser.org |
| **Postman** or **Insomnia** | Test and debug FastAPI endpoints during Phase 1–3 | https://www.postman.com / https://insomnia.rest |
| **Docker Desktop** | Run the `mock_gov_apis/` service in an isolated container | https://www.docker.com/products/docker-desktop |
| **Proxyman** or **Wireshark** | Verify no traffic leaves 127.0.0.1 (important for the local-only guarantee) | https://proxyman.io |

---

## 16. Datasets — Download for Testing

| Dataset | Use | Where |
|---|---|---|
| **MIDV-2020** | Identity docs with forged/edited variants — test PRNU + DCT | https://github.com/SmartEngines/midv-2020 |
| **CASIA v2** | Image splicing/copy-move ground truth — test ELA | https://github.com/namtpham/casia2groundtruth |
| **FUNSD** | Form understanding + layout/field extraction | https://guillaumejaume.github.io/FUNSD/ |
| **RVL-CDIP** | Document type classification (16 classes) — fine-tune LayoutLMv3 | https://www.cs.cmu.edu/~aharley/rvl-cdip/ |
| **SROIE** | Receipt OCR + key info extraction (proxy for financial docs) | https://rrc.cvc.uab.es/?ch=13 |
| **DocBank** | Document layout analysis pretraining | https://github.com/doc-analysis/DocBank |

---

## Quick-Start: Complete Install Script

Save as `setup.sh` and run once on a fresh machine:

```bash
#!/bin/bash
# Credexa AI — one-shot environment setup

# ── System ──────────────────────────────────────────────────
brew install node@20 python@3.11 tesseract tesseract-lang exiftool git

# ── Python packages ─────────────────────────────────────────
pip3.11 install \
  fastapi "uvicorn[standard]" python-multipart pydantic \
  pdfplumber pytesseract PyMuPDF paddleocr paddlepaddle \
  python-docx openpyxl pandas \
  pikepdf Pillow opencv-python numpy imago-forensics \
  spacy rapidfuzz dedupe indic-nlp-library \
  scikit-learn pyod \
  langchain langchain-community requests \
  transformers datasets torch sentencepiece \
  prnu

# ── spaCy models ────────────────────────────────────────────
python3.11 -m spacy download en_core_web_sm
python3.11 -m spacy download xx_ent_wiki_sm

# ── peepdf (not on PyPI) ────────────────────────────────────
pip3.11 install git+https://github.com/jesparza/peepdf.git

# ── Ollama + Qwen model ─────────────────────────────────────
# Install Ollama manually: https://ollama.com/download
# Then run:
# ollama pull qwen2.5:7b

echo "✓ Python environment ready. Install Ollama manually, then run: ollama pull qwen2.5:7b"
```

---

## Summary Table — What You're Installing and Why

| Category | Count | Key Packages |
|---|---|---|
| System binaries | 3 | tesseract, tesseract-lang, exiftool |
| Node / Electron | 8 | electron, electron-builder, concurrently, wait-on, vite, react, tailwindcss, lucide-react |
| Python: Backend | 4 | fastapi, uvicorn, python-multipart, pydantic |
| Python: OCR | 5 | pdfplumber, pytesseract, PyMuPDF, paddleocr, paddlepaddle |
| Python: Office formats | 3 | python-docx, openpyxl, pandas |
| Python: Forensics | 6 | pikepdf, Pillow, opencv-python, numpy, imago-forensics, peepdf |
| Python: Visual | 2–3 | prnu, CNNDetection, ManTraNet (stretch) |
| Python: NLP | 5 + 2 models | spaCy, rapidfuzz, dedupe, indic-nlp-library + en/xx models |
| Python: ML | 2 | scikit-learn, pyod |
| Python: LLM | 3 | langchain, langchain-community, requests |
| Python: DL (classifier) | 4 | transformers, datasets, torch, sentencepiece |
| AI Models | 4 | qwen2.5:7b (Ollama), layoutlmv3-base (HF), en_core_web_sm, xx_ent_wiki_sm |
| Fonts | 2 | Inter, JetBrains Mono |
| VS Code Extensions | 9 | python, pylance, tailwindcss, eslint, prettier, sqlite-viewer, rest-client, rainbow-csv, md-preview |
| Desktop Tools | 4 | TablePlus, Postman, Docker Desktop, Proxyman |