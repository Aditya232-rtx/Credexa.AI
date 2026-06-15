### Document Fraud Detection for Loan Underwriting — Build Guide & Implementation Plan

## Problem Statement
"Real-time anomaly detection
How can a bank automatically detect tampering or changes or forgery attempts made across land records, legal documents and financial statements in real time and provide intelligent insights to support faster, reliable decision-making during underwriting."

This guide maps every block in the production architecture diagram to a concrete open-source tool, a prototype-scale implementation note, and reference links. Scope is hackathon/prototype
level: local models, mocked government APIs, single-machine deployment — but each module is
swappable for a production equivalent without changing the pipeline shape.

---

## 1. System Recap

```
Upload → OCR + Metadata → Doc Type Router (LayoutLMv3)
   ├── Financial Bucket  → Native PDF / Screenshot path → Metadata+Font / ELA+Texture → Math Validator → TRACES/CBDT check
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

## 2. Component-by-Component Build Guide

### 2.1 Ingestion — OCR & Text Extraction

| Tool | Use | Link |
|---|---|---|
| pdfplumber | Native PDF text/table extraction | https://github.com/jsvine/pdfplumber |
| Tesseract OCR | OCR for scanned/image documents | https://github.com/tesseract-ocr/tesseract |
| PaddleOCR | Stronger OCR + layout detection, good for Indian scripts | https://github.com/PaddlePaddle/PaddleOCR |
| pytesseract | Python wrapper for Tesseract | https://github.com/madmaze/pytesseract |

**Implementation note:** Try pdfplumber first (native PDFs return clean text + bounding boxes).
If text extraction returns empty/garbage → fall back to PaddleOCR/Tesseract on rasterized pages
(PyMuPDF can rasterize a PDF page to image).

---

### 2.2 Metadata Capture

| Tool | Use | Link |
|---|---|---|
| ExifTool | Full metadata dump (creation tool, timestamps, edit history) | https://exiftool.org/ |
| Apache Tika | Metadata + content extraction across file types | https://tika.apache.org/ |
| PyMuPDF (fitz) | PDF-specific metadata, page rendering, XObject inspection | https://github.com/pymupdf/PyMuPDF |
| pikepdf (qpdf wrapper) | PDF structure/object inspection — detect overlay layers | https://github.com/pikepdf/pikepdf |

**Implementation note:** `exiftool -j file.pdf` gives JSON metadata in one call — flag if
`Producer`/`Creator` looks inconsistent with the claimed document source (e.g. a "bank-issued"
PDF whose Producer is `Microsoft Print to PDF` or edited in `Adobe Acrobat Pro` hours after the
claimed issue date). pikepdf can enumerate content streams to detect a text layer pasted over
an image layer (classic whiting-out + retype).

---

### 2.3 Document Type Router / Classifier

| Tool | Use | Link |
|---|---|---|
| LayoutLMv3 (base) | Layout-aware document classification | https://huggingface.co/microsoft/layoutlmv3-base |
| Donut (Document Understanding Transformer) | OCR-free document classification/parsing | https://github.com/clovaai/donut |
| RVL-CDIP dataset | Pretraining/fine-tuning data for doc classification | https://www.cs.cmu.edu/~aharley/rvl-cdip/ |

**Implementation note:** For prototype speed, fine-tune LayoutLMv3-base on a small labeled set
(bank statement / ITR / sale deed / Aadhaar / 7-12 extract / PoA, ~30-50 samples per class is
enough for a demo-grade classifier). If time is tight, a zero-shot approach using the extracted
OCR text + a prompt to a local LLM (Qwen2.5-7B via Ollama) for classification is a fast fallback.

---

### 2.4 File Forensics (PDF layer / edit history)

| Tool | Use | Link |
|---|---|---|
| pikepdf | Inspect PDF object structure, content streams, layers | https://github.com/pikepdf/pikepdf |
| peepdf | PDF forensic analysis (suspicious objects, JS, structure) | https://github.com/jesparza/peepdf |
| ExifTool | Edit-history/timestamp anomalies | https://exiftool.org/ |
| Imago Forensics | Combined metadata + ELA + thumbnail forensic toolkit | https://github.com/redaelli/imago-forensics |

**Implementation note:** Flag conditions: multiple `/Type /XObject` overlapping bounding boxes
on the same region, mismatched font subsets (`/FontFile` entries inconsistent across pages),
or `ModifyDate` significantly later than `CreateDate` with a different `Producer`.

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

**Implementation note for ELA (quick build):** resave the image at JPEG quality 90, compute
pixel-wise absolute difference with the original, amplify the difference map. Regions that were
edited after the last save show up as bright blocks against a uniformly dark background. This
is ~30 lines of Pillow/numpy and is the highest ROI forensic check for the time it takes to build.

For **DCT/double-compression analysis** (detects re-saved/edited JPEGs), the "JPEG Ghost"
technique is well documented and implementable with numpy + OpenCV's DCT functions.

---

### 2.6 Logic / Mathematical Consistency (Math Validator)

No external library needed — this is pure business logic over the OCR-extracted fields.

| Check | Formula |
|---|---|
| Bank statement | `opening_balance + Σcredits − Σdebits == closing_balance` (per transaction line and overall) |
| Balance Sheet | `Assets == Liabilities + Equity` |
| P&L | `Gross Revenue − COGS − OpEx == Net Income` |
| ITR vs Form 26AS | declared income ≈ TDS-implied income within tolerance |

**Implementation note:** Use `pandas` + `re`/regex to extract amount columns from OCR text,
normalize Indian number formats (lakhs/crores, commas), then run reconciliation with a small
tolerance band (e.g. ±1%) to allow for OCR rounding noise.

---

### 2.7 Cross-Document Consistency Engine

| Tool | Use | Link |
|---|---|---|
| RapidFuzz | Fast fuzzy string matching for names/addresses across docs | https://github.com/rapidfuzz/RapidFuzz |
| spaCy | Named entity extraction (names, dates, amounts, addresses) | https://spacy.io/ |
| dedupe | Entity resolution across records | https://github.com/dedupeio/dedupe |
| indic-nlp-library | Helps normalize Indian names/addresses (transliteration variants) | https://github.com/anoopkunchukuttan/indic_nlp_library |

**Implementation note:** Extract `{name, address, DOB/PAN, income, dates}` per document via
spaCy NER + regex, then run RapidFuzz `token_sort_ratio` pairwise across documents. Below a
similarity threshold (e.g. 85%) → flag as a cross-document inconsistency, surfaced with the
two conflicting values side by side for the explainability engine.

---

### 2.8 External Ground Truth (mocked for prototype)

Real government APIs (TRACES, MCA21, Account Aggregator) require institutional access/MoUs and
are **not directly callable** in a hackathon context — build a mock service layer with the same
interface so it's a drop-in swap later.

| Real Source | Reference | Prototype Approach |
|---|---|---|
| Form 26AS / TRACES (TDS credits) | https://www.tdscpc.gov.in/ | Mock JSON endpoint returning sample TDS records |
| MCA21 (corporate filings) | https://www.mca.gov.in/ | Mock endpoint / scrape-able public search for demo company names |
| Account Aggregator framework | https://sahamati.org.in/ | Mock FI-data response in AA's published JSON schema |
| Maharashtra land records (7/12, Property Card) | https://bhulekh.mahabhumi.gov.in/ | Mock response keyed by survey number for demo |

**Implementation note:** Build a tiny FastAPI service `mock_gov_apis/` with endpoints
`/traces/26as`, `/mca/company`, `/aa/fi-data`, `/bhulekh/712` returning canned JSON for a handful
of demo identities — this lets the External Ground Truth block run end-to-end in the demo while
making clear in your docs/pitch which calls become real integrations post-MoU.

---

### 2.9 ML Anomaly Engine

| Tool | Use | Link |
|---|---|---|
| scikit-learn (Isolation Forest) | Unsupervised outlier detection on numeric features | https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.IsolationForest.html |
| PyOD | Broader anomaly detection toolkit (multiple algorithms) | https://github.com/yzhao062/pyod |
| spaCy / Qwen2.5 (via Ollama) | NLP extractor — entities, semantic cross-checks | https://spacy.io/ , https://ollama.com/ |
| pandas | Pattern detector — round-number frequency, transaction sequence stats | https://pandas.pydata.org/ |

**Implementation note:** Feature set for Isolation Forest: transaction amount distribution
stats (mean, std, % round numbers), balance volatility, income-to-credit ratio, date-gap
irregularities, OCR-confidence scores per field. Train on a set of "genuine" sample documents
(synthetic is fine for demo) so the model has a baseline of "normal."

---

### 2.10 Score Aggregation + Explainability Engine

| Tool | Use | Link |
|---|---|---|
| Custom weighted scoring (Python) | Combine per-layer flags into 0–100 risk score | — |
| Ollama | Local LLM serving for explanation generation | https://ollama.com/ |
| Qwen2.5-7B-Instruct (or your existing Qwen2.5-Coder-7B setup) | Generates natural-language reasoning from structured flags | https://huggingface.co/Qwen/Qwen2.5-7B-Instruct |
| LangChain (optional) | Prompt templating / structured output parsing | https://github.com/langchain-ai/langchain |

**Implementation note:** Score aggregator = weighted sum across the 5 detection layers
(weights tunable, start with equal weighting and adjust per layer's false-positive rate).
Explainability engine takes the structured flag list (e.g.
`{"font_mismatch": "page 3", "balance_reconciliation": "off by ₹14,200", "cross_doc_name_mismatch": "Aadhaar vs ITR"}`)
and prompts the LLM with a fixed template: *"Given these detected anomalies, write a 2-3
sentence explanation for an underwriter, citing specific evidence."* Keep the LLM out of the
scoring decision itself — it only explains, the score is deterministic/auditable.

---

### 2.11 Output Layer

| Tool | Use | Link |
|---|---|---|
| Streamlit | Fastest path to an underwriter dashboard for a prototype | https://streamlit.io/ |
| Next.js + Tailwind | If you want a polished dashboard matching your usual stack | https://nextjs.org/ , https://tailwindcss.com/ |
| FastAPI | Backend API serving scores/flags/explanations | https://fastapi.tiangolo.com/ |
| SQLite / PostgreSQL | Case management + audit log storage | https://www.sqlite.org/ , https://www.postgresql.org/ |

**Implementation note:** Audit log = append-only table (`document_id, timestamp, layer,
flag, score_delta, reviewer_action`). For "auto-route vs auto-approve," a simple threshold
(e.g. score < 20 → auto-approve, 20-60 → reviewer queue, >60 → escalate) is enough for a demo.

---

### 2.12 Feedback Loop

**Implementation note:** Log every reviewer decision (`approved` / `rejected` / `escalated`)
against the document's feature vector. For the prototype, a periodic script that re-fits the
Isolation Forest on the accumulated "approved = normal" samples demonstrates the loop without
needing a full MLOps pipeline. Document this as the production hook for continuous retraining.

---

## 3. Datasets for Training / Testing

| Dataset | Use | Link |
|---|---|---|
| MIDV-2020 | Identity documents incl. forged/edited variants | https://github.com/SmartEngines/midv-2020 |
| FUNSD | Form understanding — layout/field extraction | https://guillaumejaume.github.io/FUNSD/ |
| DocBank | Document layout analysis pretraining | https://github.com/doc-analysis/DocBank |
| RVL-CDIP | Document type classification (16 classes) | https://www.cs.cmu.edu/~aharley/rvl-cdip/ |
| CASIA v2 Tampering Detection | Image splicing/copy-move ground truth for ELA testing | https://github.com/namtpham/casia2groundtruth |
| SROIE | Receipt OCR + key info extraction (good proxy for financial docs) | https://rrc.cvc.uab.es/?ch=13 |

For India-specific financial/legal document samples, generate **synthetic** bank statements,
ITRs, and sale deeds using your existing document-generation skills (LibreOffice/python-docx →
PDF), then programmatically apply known tampering (edit a number, change a font, recompress an
image region) to create labeled "forged" pairs for testing each forensic module.

---

## 4. Suggested Repo Structure

```
fraud-detection/
├── ingestion/
│   ├── ocr.py              # pdfplumber + PaddleOCR/Tesseract fallback
│   └── metadata.py          # ExifTool/Tika wrapper
├── router/
│   └── classifier.py        # LayoutLMv3 fine-tuned doc-type classifier
├── forensics/
│   ├── file_forensics.py     # pikepdf/peepdf checks
│   ├── visual_forensics.py   # ELA, PRNU, DCT, GAN artifact
│   └── math_validator.py     # reconciliation rules
├── consistency/
│   └── cross_doc.py          # spaCy NER + RapidFuzz matching
├── mock_gov_apis/
│   └── main.py               # FastAPI mock TRACES/MCA21/AA/Bhulekh endpoints
├── anomaly/
│   ├── isolation_forest.py
│   ├── nlp_extractor.py
│   └── pattern_detector.py
├── scoring/
│   ├── aggregator.py
│   └── explainability.py     # Ollama/Qwen prompt + response parsing
├── api/
│   └── main.py               # FastAPI orchestration endpoint
├── dashboard/
│   └── app.py                # Streamlit dashboard
├── db/
│   └── schema.sql            # cases, audit_log, feedback tables
└── data/
    └── synthetic_samples/    # genuine + tampered demo documents
```

---

## 5. Build Phases (prototype/hackathon pace)

**Phase 1 — Core pipeline skeleton**
Ingestion (OCR + metadata) → mock router (rule-based by filename/keywords is fine initially) →
FastAPI orchestration that strings stages together end to end with stub outputs. Goal: a
document goes in, *something* comes out at every stage.

**Phase 2 — Highest-ROI detectors**
ELA implementation (Pillow), Math Validator (pandas reconciliation), Metadata forensics
(ExifTool). These three alone catch a large share of common tampering and are each buildable
in a few hours.

**Phase 3 — Cross-document + scoring**
spaCy NER + RapidFuzz cross-doc matching, weighted score aggregator, mock external ground-truth
APIs.

**Phase 4 — ML anomaly + explainability**
Isolation Forest on synthetic genuine/forged feature sets, Ollama + Qwen2.5 explainability
prompt wired to the structured flags.

**Phase 5 — Dashboard + polish**
Streamlit (or Next.js) dashboard showing risk score, flags, and the LLM explanation per
document; audit log table; feedback-loop logging stub.

**Stretch (if time allows)**
LayoutLMv3 fine-tuned classifier (replaces rule-based router), PRNU/GAN-artifact checks for
identity documents.

---

## 6. Deployment Notes

- Everything above runs comfortably on a single machine with a GPU for the LLM (Ollama +
  Qwen2.5-7B quantized) — CPU-only also works with a smaller model (e.g. `qwen2.5:3b`) for demo
  purposes.
- Containerize each stage (Docker) so the mock government APIs can later be swapped for real
  integrations without touching the rest of the pipeline.
- Use `n8n` (https://n8n.io/) if you'd rather orchestrate the pipeline visually instead of a
  custom FastAPI orchestrator — fits your existing MCP-connected n8n setup and makes the
  stage-by-stage flow easy to demo live.

---

## 7. Quick-Reference Link List

- pdfplumber — https://github.com/jsvine/pdfplumber
- Tesseract OCR — https://github.com/tesseract-ocr/tesseract
- PaddleOCR — https://github.com/PaddlePaddle/PaddleOCR
- ExifTool — https://exiftool.org/
- Apache Tika — https://tika.apache.org/
- PyMuPDF — https://github.com/pymupdf/PyMuPDF
- pikepdf — https://github.com/pikepdf/pikepdf
- peepdf — https://github.com/jesparza/peepdf
- Imago Forensics — https://github.com/redaelli/imago-forensics
- LayoutLMv3 — https://huggingface.co/microsoft/layoutlmv3-base
- Donut — https://github.com/clovaai/donut
- RVL-CDIP — https://www.cs.cmu.edu/~aharley/rvl-cdip/
- PRNU-Python — https://github.com/polimi-ispl/prnu-python
- CNNDetection — https://github.com/peterwang512/CNNDetection
- ManTraNet — https://github.com/ISICV/ManTraNet
- OpenCV — https://github.com/opencv/opencv
- RapidFuzz — https://github.com/rapidfuzz/RapidFuzz
- spaCy — https://spacy.io/
- dedupe — https://github.com/dedupeio/dedupe
- indic-nlp-library — https://github.com/anoopkunchukuttan/indic_nlp_library
- scikit-learn IsolationForest — https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.IsolationForest.html
- PyOD — https://github.com/yzhao062/pyod
- Ollama — https://ollama.com/
- Qwen2.5-7B-Instruct — https://huggingface.co/Qwen/Qwen2.5-7B-Instruct
- LangChain — https://github.com/langchain-ai/langchain
- Streamlit — https://streamlit.io/
- FastAPI — https://fastapi.tiangolo.com/
- n8n — https://n8n.io/
- MIDV-2020 — https://github.com/SmartEngines/midv-2020
- FUNSD — https://guillaumejaume.github.io/FUNSD/
- DocBank — https://github.com/doc-analysis/DocBank
- CASIA v2 — https://github.com/namtpham/casia2groundtruth
- SROIE — https://rrc.cvc.uab.es/?ch=13
- TRACES — https://www.tdscpc.gov.in/
- MCA21 — https://www.mca.gov.in/
- Sahamati (Account Aggregator) — https://sahamati.org.in/
- Maharashtra Bhulekh — https://bhulekh.mahabhumi.gov.in/
