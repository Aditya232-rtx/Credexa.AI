# Credexa — AI Document Fraud Detection for Underwriting

Welcome to **Credexa**, a comprehensive desktop application for detecting tampering, forgery, and anomalies across land records, legal documents, and financial statements in real time. This system provides intelligent insights to support faster, more reliable decision-making during the loan underwriting process.

## 🚀 Overview

How can a bank automatically detect tampering or changes made across land records, legal documents, and financial statements in real time? Credexa solves this by offering a multi-layered pipeline that ingests documents, categorizes them, extracts forensic metadata, applies visual and logical validation, and surfaces anomalies to the underwriter with an LLM-powered explainability engine.

### Core Pipeline
1. **Ingestion**: OCR & Text/Metadata Extraction (pdfplumber, Tesseract, PaddleOCR)
2. **Document Routing**: Categorizes documents into Financial, Legal, or Land & Identity using LayoutLMv3.
3. **Forensic Analysis**:
   - **File Forensics**: Inspects PDF layers, object structure, and edit history.
   - **Visual Forensics**: Performs Error Level Analysis (ELA), DCT block analysis, and PRNU noise fingerprinting.
   - **Logical/Math Validation**: Cross-checks financial equations (e.g., Bank balance reconciliation, Assets = Liabilities + Equity).
4. **Cross-Document Consistency**: Uses NER and fuzzy matching to ensure details (Names, PAN, DOB) match across different submitted documents.
5. **ML Anomaly Engine**: Employs Isolation Forest and Pattern Detectors to flag outliers.
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
| **Classification** | `LayoutLMv3`, `Donut` |
| **NLP & Matching** | `spaCy`, `RapidFuzz` |
| **ML & Analytics** | `scikit-learn`, `pandas` |
| **Explainability** | `Ollama`, `Qwen2.5-7B` |
| **Backend API** | `FastAPI`, `SQLite`, `Uvicorn` |
| **Frontend** | `React`, `Vite`, `Tailwind CSS` |
| **Desktop App** | `Electron` |

---

## 🛠 Setup & Installation

### Prerequisites

| Requirement | macOS | Windows |
|------------|-------|---------|
| **Python** | `python3.11` (via Homebrew or pyenv) | Python 3.11 from [python.org](https://www.python.org/downloads/) |
| **Node.js** | v18+ (via Homebrew or nvm) | v18+ from [nodejs.org](https://nodejs.org/) |
| **Git** | Pre-installed | [git-scm.com](https://git-scm.com/downloads) |

---

### macOS Setup

```bash
# 1. Clone the repository
git clone https://github.com/Aditya232-rtx/Credexa.git
cd Credexa

# 2. Create Python virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# 3. Install Python dependencies
pip install -r backend/requirements.txt

# 4. Install frontend dependencies
cd frontend
npm install

# 5. Run the app (starts backend + Electron)
npm run dev
```

The Electron app will open automatically. The backend (FastAPI on port 8765) is launched by Electron.

---

### Windows Setup

> **Important**: Make sure Python 3.11 is installed and added to your system `PATH` during installation (check the box "Add Python to PATH" in the installer).

#### Step 1: Clone the Repository

```powershell
git clone https://github.com/Aditya232-rtx/Credexa.git
cd Credexa
```

#### Step 2: Create a Python Virtual Environment

```powershell
# Using Command Prompt (cmd)
python -m venv .venv
.venv\Scripts\activate

# OR using PowerShell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

> **PowerShell Execution Policy**: If you get a "running scripts is disabled" error in PowerShell, run this first:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

#### Step 3: Install Python Dependencies

```powershell
pip install -r python\requirements.txt
```

#### Step 4: Install Frontend Dependencies

```powershell
cd frontend
npm install
```

#### Step 5: Run the Application

```powershell
# Windows needs a slightly different dev script since wait-on syntax differs.
# Option A: Use the cross-platform dev command
npm run dev

# Option B: If the above fails, start backend and frontend separately:

# Terminal 1 — Start the backend
cd ..\python
..\.venv\Scripts\python -m uvicorn api.main:app --host 127.0.0.1 --port 8765

# Terminal 2 — Start the frontend + Electron
cd frontend
npx vite
# Then in Terminal 3:
set NODE_ENV=development && npx electron .
```

#### Troubleshooting on Windows

| Issue | Solution |
|-------|---------|
| `python` not found | Ensure Python 3.11 is on your PATH. Try `py -3.11` instead of `python`. |
| `npm run dev` hangs | The `wait-on` package may behave differently. Use Option B above (manual start). |
| Electron white screen | Backend may not have started. Check that port 8765 is responding: `curl http://127.0.0.1:8765/health` |
| PowerShell script error | Run `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser` |
| `node-gyp` build errors | Install Windows Build Tools: `npm install -g windows-build-tools` |
| Permission denied on `.venv` | Run your terminal as Administrator, or use `cmd` instead of PowerShell. |

---

### Linux Setup

```bash
# 1. Clone
git clone https://github.com/Aditya232-rtx/Credexa.git
cd Credexa

# 2. Virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r backend/requirements.txt
cd frontend && npm install

# 4. Run
npm run dev
```

---

## 📂 Project Structure

```
Credexa/
├── frontend/               # React + Vite + Electron desktop app
│   ├── electron/           # Electron main process (main.js, preload.js)
│   ├── src/                # React application source
│   │   ├── components/     # Shared UI components (Sidebar, Toast, DocumentCard)
│   │   ├── views/          # Page views (Dashboard, CaseDetail, Upload)
│   │   ├── api.js          # Backend API client
│   │   └── App.jsx         # Main app shell
│   └── package.json
├── backend/                 # FastAPI backend + ML pipeline
│   ├── api/                # REST API endpoints
│   ├── db/                 # SQLite schema
│   ├── services/           # Analysis pipeline, document router
│   ├── mock_gov_apis/      # Mock government verification APIs
│   └── requirements.txt
├── docs/                   # Documentation, architecture diagrams
└── README.md
```

## 📄 License

This project is licensed under the MIT License.
