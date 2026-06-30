# Credexa — AI Document Fraud Detection for Underwriting

Welcome to **Credexa**, a comprehensive desktop application for detecting tampering, forgery, and anomalies across land records, legal documents, and financial statements in real time. This system provides intelligent insights to support faster, more reliable decision-making during the loan underwriting process.

## 🚀 Overview

How can a bank automatically detect tampering or changes made across land records, legal documents, and financial statements in real time? Credexa solves this by offering a multi-layered pipeline that ingests documents, categorizes them, extracts forensic metadata, applies visual and logical validation, and surfaces anomalies to the underwriter with an LLM-powered explainability engine.

### Core Pipeline
1. **Ingestion**: OCR & Text/Metadata Extraction (pdfplumber, RapidOCR, supported by Sarvam AI API for high-accuracy Indian language OCR)
2. **Document Routing**: Categorizes documents into Financial, Legal, or Land & Identity using keyword-based classification with optional VLM-based classification (Sarvam AI).
3. **Forensic Analysis**:
   - **File Forensics**: Inspects PDF layers, object structure, fonts, and edit history.
   - **Visual Forensics**: Performs Error Level Analysis (ELA), DCT block analysis, and PRNU noise fingerprinting.
   - **AI / Tamper Detection**: Supported by Sightengine API (AI-generated image detection) and Veryfi API (digital tampering & fraud detection).
   - **Logical/Math Validation**: Cross-checks financial equations (e.g., Bank balance reconciliation, Assets = Liabilities + Equity).
4. **Cross-Document Consistency**: Uses NER and fuzzy matching to ensure details (Names, PAN, DOB) match across different submitted documents.
5. **ML Anomaly Engine**: Employs Isolation Forest, ECOD, Autoencoder, and Pattern Detectors to flag outliers.
6. **Score Aggregation & Explainability**: Calculates a definitive risk score, and generates a natural-language explanation using Sarvam AI's LLM.

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
| **OCR & Extraction** | `pdfplumber`, `RapidOCR`, `Sarvam AI API` (high-accuracy Indian language OCR) |
| **Metadata & Forensics** | `ExifTool`, `pikepdf`, `Pillow` (ELA), `Sightengine API` (AI detection), `Veryfi API` (tamper detection) |
| **Classification & NLP** | `spaCy`, `RapidFuzz`, `Sarvam AI VLM` (vision-based document classification) |
| **ML & Analytics** | `scikit-learn`, `pandas`, `Isolation Forest` |
| **Backend API** | `FastAPI`, `Uvicorn` |
| **Database** | `SQLite` (default), `PostgreSQL` (production) |
| **Frontend** | `React`, `Vite`, `Tailwind CSS` |
| **Desktop App** | `Electron` |

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

### Desktop App Build (macOS)

To package Credexa as a standalone macOS desktop application:

```bash
cd frontend
npm install
npm run electron:build -- --mac
```

The packaged `.dmg` file will be available in the `frontend/dist_electron/` directory.

### Desktop App Build (Windows)

To package Credexa as a standalone Windows desktop application:

```powershell
cd frontend
npm install
npm run electron:build -- --win
```

The packaged installer (`.exe` / `.msi`) will be available in the `frontend/dist_electron/` directory.

> **Note**: For Windows builds, you may need to configure code signing or run without signing for local testing. See Electron Builder documentation for details.

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
├── backend/                # FastAPI backend
│   ├── api/                # REST API endpoints
│   ├── db/                 # SQLite / PostgreSQL dual-backend
│   ├── services/           # Analysis pipeline, external API integrations
│   ├── consistency/        # Cross-document & applicant data checks
│   ├── forensics/          # File, visual, and math validation
│   ├── scoring/            # Risk scoring & explainability
│   ├── ner/                # Indian PII extraction & entity recognition
│   └── router/             # Document classifier
├── docker-compose.yml      # Multi-container orchestration
├── requirements.txt        # Python dependencies
├── docs/                   # Documentation, architecture diagrams
└── README.md
```

## 📥 Direct Desktop App Download

Pre-built desktop installers for Windows and macOS will be available for direct download soon. Stay tuned for the first release with one-click installation — no manual setup required.

---

## 📄 License

This project is licensed under the MIT License.
