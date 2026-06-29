# Credexa — AI Document Fraud Detection for Underwriting

Welcome to **Credexa**, a comprehensive desktop application for detecting tampering, forgery, and anomalies across land records, legal documents, and financial statements in real time. This system provides intelligent insights to support faster, more reliable decision-making during the loan underwriting process.

## 🚀 Overview

How can a bank automatically detect tampering or changes made across land records, legal documents, and financial statements in real time? Credexa solves this by offering a multi-layered pipeline that ingests documents, categorizes them, extracts forensic metadata, applies visual and logical validation, and surfaces anomalies to the underwriter with an LLM-powered explainability engine.

### Core Pipeline
1. **Ingestion**: OCR & Text/Metadata Extraction (pdfplumber, RapidOCR, PaddleOCR)
2. **Document Routing**: Categorizes documents into Financial, Legal, or Land & Identity using keyword-based classification with LayoutLMv3 as an optional signal.
3. **Forensic Analysis**:
   - **File Forensics**: Inspects PDF layers, object structure, fonts, and edit history.
   - **Visual Forensics**: Performs Error Level Analysis (ELA), DCT block analysis, and PRNU noise fingerprinting.
   - **Logical/Math Validation**: Cross-checks financial equations (e.g., Bank balance reconciliation, Assets = Liabilities + Equity).
4. **Cross-Document Consistency**: Uses NER and fuzzy matching to ensure details (Names, PAN, DOB) match across different submitted documents.
5. **ML Anomaly Engine**: Employs Isolation Forest, ECOD, Autoencoder, and Pattern Detectors to flag outliers.
6. **Score Aggregation & Explainability**: Calculates a definitive risk score, and uses a local LLM (e.g., Qwen) to generate a natural-language explanation of why a document was flagged.

### Application Types Supported
Credexa supports document verification across multiple use cases:
- **Loan** — Home Loan, Business Loan, Mortgage Loan, Vehicle Loan, Crop Loan, Gold Loan, Personal Loan, Education Loan
- **Insurance** — Life, Health, Vehicle, Property, Crop Insurance
- **KYC Verification** — Individual KYC, Business KYC, Enhanced Due Diligence
- **Account Opening** — Savings Account, Current Account, Fixed Deposit, Demat Account
- **Property Registration** — Sale Deed, Gift Deed, Mortgage Registration, Lease Registration
- **Tax Filing** — ITR Filing, GST Registration, TDS Return, Corporate Tax

## 📁 Supported Document Types

Credexa is built to handle the complexities of regional and standard documents:

- **Land & Property Records**: 7/12 Extract, Property Cards, Sale Deeds, Mortgages, Encumbrance Certificates.
- **Legal & Identity Documents**: Aadhaar, PAN, Passport, MoA/AoA, Board Resolutions, Power of Attorney.
- **Financial Statements & Tax Registries**: Bank Statements, Balance Sheets, P&L, Form 16, Form 26AS, Corporate Tax Returns.

## 🏗 System Architecture

![Credexa Architecture](docs/mermaid-diagram-2026-06-15-213554.png)

*The pipeline maps every block to a concrete open-source tool, ready for both local prototype scaling and production deployment.*

## 💻 Tech Stack & Tooling

| Layer | Technologies |
|-------|-------------|
| **OCR & Extraction** | `pdfplumber`, `Tesseract`, `PaddleOCR` |
| **Metadata & Forensics** | `ExifTool`, `pikepdf`, `Pillow` (ELA), `Imago Forensics` |
| **Classification & NLP** | `LayoutLMv3`, `Donut`, `spaCy`, `RapidFuzz` |
| **ML & Analytics** | `scikit-learn`, `pandas`, `Isolation Forest` |
| **Backend API** | `FastAPI`, `Uvicorn` |
| **Database & Task Queue** | `PostgreSQL`, `Redis`, `Celery` |
| **Frontend** | `React`, `Vite`, `Tailwind CSS` |
| **Desktop App** | `Electron` |

---

## 🧠 Model Optimization (LayoutLMv3)

Credexa uses LayoutLMv3 for document parsing and routing. By default, the raw PyTorch model from HuggingFace is extremely large (~478MB). Running this raw model inside parallel Celery workers creates a massive memory bottleneck, especially during local development or on CPU-only infrastructure.

To solve this, we use **PyTorch QNNPACK INT8 Dynamic Quantization**. This process compresses the model weights, slashing the memory footprint by **~51% (down to 235MB)** and dramatically speeding up CPU inference without losing extraction accuracy.

### Generating the Optimized Model
If you are running Credexa locally, you should generate the optimized `.pt` model before starting the backend.

1. Activate your virtual environment.
2. Run the optimization script:
```bash
python export_pytorch_quantized.py
```
3. The script will download the raw FUNSD model, apply INT8 quantization, and save `layoutlmv3_quantized.pt` to the root directory.
4. The OCR ingestion engine (`backend/ingestion/ocr.py`) will automatically detect and load this smaller, faster model.

---

## 🛠 Setup & Installation

### Option A: Using Docker Compose (Recommended)
This is the fastest way to get everything running, as it spins up PostgreSQL, Redis, the Celery Worker, the FastAPI backend, and the React frontend automatically.

1. **Clone the repository:**
```bash
git clone https://github.com/Aditya232-rtx/Credexa.git
cd Credexa
```

2. **Start the containers:**
```bash
docker-compose up --build
```
*The FastAPI backend will be available at `http://localhost:8765` and the React frontend at `http://localhost:5173`.*

---

### Option B: Local Native Setup (macOS / Linux)

If you prefer to run the services natively without Docker, ensure you have **PostgreSQL (v14+)** and **Redis (v7+)** installed and running on default ports.

1. **Clone the repository and set up a virtual environment:**
```bash
git clone https://github.com/Aditya232-rtx/Credexa.git
cd Credexa
python3.11 -m venv .venv
source .venv/bin/activate
```

2. **Install Python Backend Dependencies:**
```bash
pip install -r requirements.txt
```

3. **Start the Celery Worker:**
*(Note: On macOS, use `--pool=solo` to avoid PyTorch fork issues).*
```bash
cd backend
OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES celery -A celery_app worker --pool=solo --loglevel=info
```

4. **Start the FastAPI Backend:**
Open a new terminal, activate the venv, and run:
```bash
cd backend
uvicorn api.main:app --host 127.0.0.1 --port 8765

source venv/bin/activate && cd backend && uvicorn api.main:app --host 127.0.0.1 --port 8765 --reload 2>&1 | head -30
```

5. **Start the Frontend & Electron App:**
Open a third terminal:
```bash
cd frontend
npm install
npm run dev
```

---

### Option C: Local Native Setup (Windows)

> **Important**: Ensure PostgreSQL and Redis are running locally. You may need to use WSL2 for Redis, or a Windows port.

1. **Setup Environment:**
```powershell
git clone https://github.com/Aditya232-rtx/Credexa.git
cd Credexa
python -m venv .venv
.venv\Scripts\activate
```

2. **Install Dependencies:**
```powershell
pip install -r requirements.txt
```

3. **Start Celery Worker (Terminal 1):**
```powershell
cd backend
celery -A celery_app worker --pool=solo --loglevel=info
```

4. **Start FastAPI Backend (Terminal 2):**
```powershell
cd backend
uvicorn api.main:app --host 127.0.0.1 --port 8765
```

5. **Start Frontend (Terminal 3):**
```powershell
cd frontend
npm install
npm run dev
```

## 📂 Project Structure

```
Credexa/
├── frontend/               # React + Vite + Electron desktop app
│   ├── electron/           # Electron main process (main.js, preload.js)
│   ├── src/                # React application source
│   ├── package.json
├── backend/                # FastAPI backend + ML pipeline + Celery
│   ├── api/                # REST API endpoints
│   ├── db/                 # SQLite / PostgreSQL dual-backend (connection.py)
│   ├── services/           # Analysis pipeline, document router (QuickScanPipeline available)
│   ├── ingestion/          # LayoutLMv3, PyMuPDF extractors
│   ├── celery_app.py       # Celery worker & Redis configuration
│   ├── tasks.py            # Async background tasks
│   └── mock_gov_apis/      # Mock government verification APIs
├── docker-compose.yml      # Multi-container orchestration
├── Dockerfile              # Backend container build instructions
├── requirements.txt        # Python dependencies
├── docs/                   # Documentation, architecture diagrams
└── README.md
```

## 🧠 Model Quantization & `.pt` Models

Our analysis pipeline heavily relies on Deep Learning models, primarily **LayoutLMv3** for understanding document structure (key-value pair extraction) and semantic labeling.
By default, the raw LayoutLMv3 PyTorch model is approximately 500MB and uses FP32 (32-bit floating point) precision. 

Running this raw model inside a Celery background worker on CPU poses severe bottlenecks:
1. **High Memory Usage**: Multiple worker threads loading FP32 models can quickly OOM (Out Of Memory) the unified memory of the host machine.
2. **Inference Latency**: Without optimization, token classification on high-resolution OCR bounds takes several seconds per page, completely blocking the Celery queue.

To solve this, we use **Dynamic INT8 Quantization** and save the optimized weights as `.pt` (PyTorch) models. Quantization reduces the model precision from 32-bit floats to 8-bit integers for the linear layers, effectively halving the memory footprint to ~240MB and providing a 2x-3x speedup on CPU inference via the `qnnpack` backend.

### Generating the Optimized Models
We have provided export scripts in the project root to generate these `.pt` models. Run the following script once before starting the backend:

```bash
# Ensure you are in your virtual environment
source venv/bin/activate

# Run the PyTorch quantization script
python3 export_pytorch_quantized.py
```
This script will download the `nielsr/layoutlmv3-finetuned-funsd` model, apply PyTorch INT8 dynamic quantization, and save the output as `layoutlmv3_quantized.pt`. The backend `ocr.py` is configured to automatically load this `.pt` file if it exists, bypassing the unoptimized HuggingFace model.

## 📄 License

This project is licensed under the MIT License.
