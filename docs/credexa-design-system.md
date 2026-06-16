# Credexa AI — Design System & Desktop Application Guide

**Product:** Credexa AI — Document Fraud Intelligence Platform  
**Target:** macOS desktop application (local, no cloud dependency)  
**Aesthetic:** Clinical minimalism — beminimalist.co-inspired, white-first, data-forward, trust-coded

---

## 1. Desktop Technology Recommendation

### Recommended: Electron + Python subprocess

For your specific situation — a web-capable developer with an entirely Python forensic backend —
**Electron** is the cleanest path to a real macOS `.app` bundle.

**Architecture:**
```
Electron main process
  └─ spawns Python subprocess (FastAPI on localhost:8765, loopback only)
  └─ loads React/Tailwind renderer
Renderer (Chromium) ←→ http://localhost:8765 (Python pipeline)
Python process
  └─ OCR, forensics, ML, scoring — all local
  └─ SQLite for audit log and case storage
```

**Why not the alternatives:**

| Option | Verdict |
|---|---|
| **Electron** ✅ | You know React/HTML/CSS. Python runs as subprocess. Polished `.app` bundle. |
| **Tauri** | Rust core — Python would need a sidecar with `tauri-plugin-shell`. Adds complexity without benefit for a prototype. |
| **PyQt6 / PySide6** | All-Python, but custom styling is painful and results look dated. Not worth the fight. |
| **CustomTkinter** | Faster to spin up than PyQt6 but UI ceiling is low. |
| **Swift/SwiftUI** | Best native macOS feel, but you'd rewrite the entire backend in Swift. Not viable. |
| **Streamlit** | Runs in browser tab, not a real desktop app. Fails the local/demo requirement. |

**Stack:**
```
Frontend:   React 18 + Vite + Tailwind CSS
Desktop:    Electron 30+
Backend:    Python 3.11 · FastAPI · Uvicorn (loopback only)
Storage:    SQLite (via python-sqlite3)
Fonts:      Inter (system/bundled) + JetBrains Mono
Icons:      Lucide Icons (lucide-react)
```

**macOS app bundle setup (in package.json):**
```json
{
  "build": {
    "appId": "ai.credexa.desktop",
    "productName": "Credexa AI",
    "mac": {
      "category": "public.app-category.finance",
      "target": "dmg",
      "icon": "assets/icon.icns"
    },
    "extraResources": [
      { "from": "../python", "to": "python", "filter": ["**/*"] }
    ]
  }
}
```

**Electron main.js — spawn Python on startup:**
```javascript
const { app, BrowserWindow } = require('electron');
const { spawn } = require('child_process');
const path = require('path');

let pythonProcess;

function startPython() {
  const pythonPath = path.join(process.resourcesPath, 'python');
  pythonProcess = spawn('python3', ['-m', 'uvicorn', 'api.main:app',
    '--host', '127.0.0.1', '--port', '8765'], { cwd: pythonPath });
}

app.whenReady().then(() => {
  startPython();
  setTimeout(createWindow, 2000);
});

app.on('will-quit', () => {
  if (pythonProcess) pythonProcess.kill();
});
```

**All data stays on-device.** The Python FastAPI server binds to `127.0.0.1` only.
Nothing leaves the machine. This is the local-first guarantee your judges want.

---

## 2. Brand Identity

**Name:** Credexa AI  
**Tagline:** *Verify. Trust. Proceed.*  
**Voice:** Expert, precise, no hedging. Like a senior underwriter who has seen everything.  
**Aesthetic bet:** Ultra-tight number typography (tracking -0.05em on JetBrains Mono values)
crossed with a clinical white-room aesthetic — beminimalist.co applied to financial tooling.
White does the heavy lifting. Semantic color (red / amber / green) carries all the risk signal.
Everything decorative has been removed; the risk score arc is the only flourish.
The interface should feel like a lab report, not a SaaS dashboard.

---

## 3. Color System

### Base Palette (Light Theme — only theme, no dark mode)

| Token | Hex | Use |
|---|---|---|
| `--paper` | `#FAFAF8` | App background — warm off-white, barely perceptible tint |
| `--sheet` | `#FFFFFF` | Title bar, sidebar, primary card surfaces |
| `--surface` | `#FFFFFF` | Cards, tables, panels — pure white on warm background |
| `--surface-raised` | `#F5F5F4` | Hover states, nested surfaces, doc panel background |
| `--border` | `#EBEBEA` | Default borders, dividers — barely-there lines |
| `--border-strong` | `#D5D5D3` | Input borders, interactive element borders |
| `--text-primary` | `#0D0D0D` | Headlines, primary values — near-black |
| `--text-secondary` | `#3A3A3A` | Body text, row names |
| `--text-muted` | `#666666` | Secondary labels, table IDs |
| `--text-dim` | `#888888` | Supporting text, summaries |
| `--text-ghost` | `#AAAAAA` | Metadata, timestamps, section labels |
| `--text-silent` | `#CCCCCA` | Ultra-faded — timestamps, inactive states |

### Accent

| Token | Hex | Use |
|---|---|---|
| `--indigo` | `#4F46E5` | Primary actions, active nav, focus rings, logo |
| `--indigo-mid` | `#6366F1` | Hover variant of indigo actions |
| `--indigo-glow` | `rgba(79,70,229,0.22)` | Logo box-shadow only |
| `--indigo-surface` | `rgba(79,70,229,0.06)` | Active nav background, drop zone hover |
| `--indigo-border` | `rgba(79,70,229,0.15)` | Active nav border |

### Semantic (Risk Signal)

On a white surface, semantic color is the *only* color in the interface.
It carries 100% of the risk communication load.

| Token | Hex | Use |
|---|---|---|
| `--alarm` | `#DC2626` | High risk, rejected, flagged |
| `--alarm-surface` | `rgba(220,38,38,0.07)` | Badge background, row tint |
| `--alarm-border` | `rgba(220,38,38,0.18)` | Badge / button borders |
| `--caution` | `#D97706` | Medium risk, review queue |
| `--caution-surface` | `rgba(217,119,6,0.08)` | Medium badge background |
| `--caution-border` | `rgba(217,119,6,0.18)` | Caution borders |
| `--clear` | `#16A34A` | Low risk, approved, verified |
| `--clear-surface` | `rgba(22,163,74,0.07)` | Clear badge background |
| `--clear-border` | `rgba(22,163,74,0.18)` | Approve button border |

### Risk Score Thresholds

```
0–19    → Clear   (#16A34A) — auto-approve eligible
20–59   → Caution (#D97706) — manual review queue
60–100  → Alarm   (#DC2626) — flag, escalate or reject
```

---

## 4. Typography

### Typefaces

| Role | Family | Notes |
|---|---|---|
| **System text** | Inter | Body, labels, UI copy — load via Google Fonts or bundle |
| **Data / Forensic** | JetBrains Mono | Risk scores, case IDs, hashes, amounts — all numeric forensic output |
| **Fallback** | system-ui, -apple-system | macOS renders system fonts beautifully as fallback |

### Type Scale

| Label | Size | Weight | Tracking | Use |
|---|---|---|---|---|
| `display` | 28px | 700 | -0.035em | Modal headings, onboarding |
| `title` | 18px | 700 | -0.025em | View titles |
| `heading` | 14px | 600 | -0.015em | Card titles, section headers |
| `body` | 12px | 400 | 0.005em | Table rows, body text |
| `label` | 11px | 500 | 0.005em | Secondary labels |
| `caption` | 10px | 500 | 0.06em + uppercase | Section tags, column headers |
| `mono-lg` | 26px | 700 | -0.05em | Stat card values |
| `mono-md` | 14px | 600 | -0.03em | Risk gauge number |
| `mono-sm` | 10.5px | 500 | 0 | Case IDs, score bars, timestamps |

---

## 5. Spacing System

Base unit: **4px**

| Token | Value | Common use |
|---|---|---|
| `space-1` | 4px | Icon padding, tight gaps |
| `space-2` | 8px | Chip padding, small gaps |
| `space-3` | 12px | List item padding |
| `space-4` | 16px | Card padding standard |
| `space-5` | 20px | Section padding |
| `space-6` | 24px | View padding |
| `space-8` | 32px | Large section gaps |

---

## 6. Border Radius System

| Token | Value | Use |
|---|---|---|
| `r-sm` | 3–4px | Chips, badges, tiny elements |
| `r-md` | 6–7px | Buttons, inputs, small cards |
| `r-lg` | 9–10px | Cards, panels, table containers |
| `r-xl` | 12px | App window |

---

## 7. Component Specifications

### Sidebar
- Width: **54px** (icon-only, no text labels)
- Background: `#FFFFFF` with `border-right: 1px solid #EBEBEA`
- Logo mark: 30×30px · solid `#4F46E5` · border-radius 7px · `box-shadow: 0 2px 8px rgba(79,70,229,0.22)`
- Nav icons: 40×40px touch target · 16×16px SVG icon (stroke-width 1.8)
- Default color: `#CCCCCA`
- Hover state: `background #F5F5F4` + `color #888888`
- Active state: `background #EEF2FF` + `border 1px #C7D2FE` + `color #4F46E5`
- Tooltip: white card, `border 1px #D5D5D3`, `box-shadow 0 2px 8px rgba(0,0,0,0.06)`, appears right of icon

### App Window (macOS simulation)
- Traffic lights: Red `#FF5F57` · Yellow `#FEBC2E` · Green `#28C840`
- Title bar height: **40px**, background `#FFFFFF`, `border-bottom 1px #EBEBEA`
- Window shadow: `0 4px 24px rgba(0,0,0,0.06), 0 1px 4px rgba(0,0,0,0.04)`
- In real Electron: use `titleBarStyle: 'hiddenInset'` to keep native traffic lights

### Buttons

| Variant | Background | Border | Text | Height |
|---|---|---|---|---|
| Primary | `#4F46E5` | none | `#fff` | 30px |
| Ghost | transparent | `1px solid #D5D5D3` | `#888888` | 30px |
| Danger | `rgba(220,38,38,0.06)` | `rgba(220,38,38,0.18)` | `#DC2626` | 29px |
| Approve | `rgba(22,163,74,0.06)` | `rgba(22,163,74,0.18)` | `#16A34A` | 29px |

All buttons: `border-radius 6px` · `font-size 11.5px` · `font-weight 500` · `padding 0 13px`

### Badges

| Variant | BG | Text |
|---|---|---|
| High risk | `rgba(220,38,38,0.07)` | `#DC2626` |
| Medium | `rgba(217,119,6,0.08)` | `#D97706` |
| Clear | `rgba(22,163,74,0.07)` | `#16A34A` |
| Category | `rgba(79,70,229,0.08)` | `#4F46E5` |
| Inactive | `rgba(120,120,120,0.08)` | `#888888` |

Height: **19px** · padding `0 7px` · border-radius `4px` · font-size `10.5px` · weight `600`

### Cards (general)
- Background: `#FFFFFF`
- Border: `1px solid #EBEBEA`
- Border-radius: `9px`
- Inner padding: `15–18px`
- No box-shadow — border alone is sufficient on a warm-white background

### Table rows
- Grid: `grid-template-columns: 95px 1fr 78px 160px 80px 76px` (dashboard default)
- Row height: ~38px (9px top/bottom padding)
- Border-bottom: `1px solid #F5F5F4` (barely perceptible on white)
- Hover: `background #FAFAF8`
- Column headers: `10px` · uppercase · `#AAAAAA` · `letter-spacing 0.06em`

### Risk Score Arc (SVG)
- Circle radius: 36px (within 96×96 viewport)
- Track color: `#EBEBEA`, stroke-width `7px`
- Fill: semantic color (alarm/caution/clear), stroke-linecap `round`
- Dash calculation: `circumference = 2π × 36 ≈ 226`. `stroke-dashoffset = 226 × (1 − score/100)`
- Center label: JetBrains Mono, 22px bold, semantic color
- Sub-label: "RISK", 8.5px, `#BBBBBB`, 0.08em tracking

---

## 8. Screen Layout Specifications

### Screen 1: Dashboard (Overview)

```
┌─ Titlebar (40px, white) ─────────────────────────────────┐
├─ Sidebar (54px, white) ─┬─ Content (FAFAF8 bg) ─────────┐
│                         │  View Header (22px top pad)     │
│  [logo: indigo square]  │  View Title · Subtitle · Btns   │
│                         ├─────────────────────────────────┤
│  [grid icon] ▲ active   │  Stats Row (4 white cards)      │
│  [file icon]            │  sc-label / sc-val / sc-sub     │
│  [upload icon]          ├─────────────────────────────────┤
│  [bar chart]            │  Main Row (flex, 12px gap)      │
│                         │  ┌─ Cases Table (white) ───────┐│
│  ·                      │  │  header + search            ││
│  ·                      │  │  col headers (10px caps)    ││
│  [settings]             │  │  table rows (hover #FAFAF8) ││
│                         │  └─────────────────────────────┘│
│                         │  ┌─ Side Panel (210px, white) ─┐│
│                         │  │  Risk Distribution bars     ││
│                         │  │  Activity feed              ││
│                         │  └─────────────────────────────┘│
└─────────────────────────┴─────────────────────────────────┘
```

### Screen 2: Case Detail

```
┌─ Titlebar (white) ───────────────────────────────────────┐
├─ Sidebar ─┬─ View Header Bordered (Back + title + badge) ┤
│           ├─ Doc Panel (260px, #FAFAF8) ─┬─ Analysis ───┤
│           │  section label               │  Risk Card    │
│           │  doc items list              │  (gauge + btns)│
│           │  ├ PDF  ● red                │  Layer cards  │
│           │  ├ ITR  ● amber              │  AI Explain   │
│           │  ├ 7-12 ● green              │               │
│           │  ├ AAD  ● green              │               │
│           │  └ Deed ● green              │               │
└───────────┴──────────────────────────────┴───────────────┘
```

### Screen 3: Upload / New Case

```
┌─ Titlebar (white) ───────────────────────────────────────┐
├─ Sidebar ─┬─ View Header (title + Cancel + Run Analysis) ┤
│           │  ┌─ Drop Zone (dashed #D5D5D3 border) ──────┐│
│           │  │  ↑ icon, title, subtitle, file pills     ││
│           │  └──────────────────────────────────────────┘│
│           │  Queue Section Label (#AAAAAA caps)           │
│           │  ┌─ Queue Item (white card) ───────────────┐  │
│           │  │  [icon] filename · size · type          │  │
│           │  │  progress bar (#EEEEEC track)           │  │
│           │  │  stage chips (green ✓ / indigo active)  │  │
│           │  └─────────────────────────────────────────┘  │
└───────────┴───────────────────────────────────────────────┘
```

---

## 9. Motion & Animation Guidelines

Credexa AI uses **zero decorative animation**. The only motion is functional:

| Element | Motion | Duration | Easing |
|---|---|---|---|
| View switch | None (instant) | — | — |
| Button hover | Background color transition | 120ms | ease |
| Nav icon hover | Color + background | 150ms | ease |
| Table row hover | Background | 100ms | ease |
| Risk gauge fill | SVG `stroke-dashoffset` animated on mount | 600ms | ease-out |
| Progress bar fill | Width animated during processing | linear | — |
| Tooltip | Opacity fade | 150ms | ease |

No slide-ins, no bounce, no parallax. Motion that isn't communicating something gets cut.

---

## 10. Icon Library

Use **Lucide Icons** (`lucide-react`): https://lucide.dev

```bash
npm install lucide-react
```

Key icons in use:

| Context | Lucide icon |
|---|---|
| Dashboard / Overview | `LayoutGrid` |
| Cases / Documents | `FileText` |
| Upload | `Upload` |
| Reports / Analytics | `BarChart2` |
| Settings | `Settings` |
| Back navigation | `ArrowLeft` |
| Risk / Flag | `AlertTriangle` |
| Approve | `CheckCircle2` |
| Reject / Danger | `XCircle` |
| Search | `Search` |
| Export | `Download` |
| Audit log | `ClipboardList` |

All icons: `size={16}` · `strokeWidth={1.8}` · color inherited from parent

---

## 11. Electron Project Setup (Step-by-Step)

```bash
# 1. Create project
mkdir credexa-desktop && cd credexa-desktop

# 2. React frontend
npm create vite@latest frontend -- --template react
cd frontend && npm install
npm install lucide-react

# 3. Install Tailwind
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p

# 4. Electron wrapper (root level)
cd ..
npm init -y
npm install --save-dev electron electron-builder concurrently wait-on

# 5. Add to root package.json
{
  "main": "electron/main.js",
  "scripts": {
    "dev": "concurrently \"npm run dev --prefix frontend\" \"wait-on http://localhost:5173 && electron .\"",
    "build": "npm run build --prefix frontend && electron-builder"
  }
}

# 6. Python setup
cd python
pip install fastapi uvicorn pdfplumber pytesseract Pillow pillow-avif-plugin \
  pikepdf pymupdf pandas scikit-learn spacy rapidfuzz python-multipart \
  --break-system-packages

# 7. Build .app
npm run build
```

**Electron main.js (minimal):**
```javascript
const { app, BrowserWindow } = require('electron');
const { spawn } = require('child_process');
const path = require('path');

let pythonProcess;

app.whenReady().then(() => {
  // Spawn Python backend
  pythonProcess = spawn('python3', [
    path.join(__dirname, '../python/api/main.py')
  ]);

  const win = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 960,
    minHeight: 680,
    titleBarStyle: 'hiddenInset',  // native macOS traffic lights
    backgroundColor: '#FFFFFF',    // prevent flash on load — match sidebar/titlebar
    webPreferences: { contextIsolation: true }
  });

  // Dev: load Vite dev server. Prod: load built index.html
  const isDev = !app.isPackaged;
  isDev
    ? win.loadURL('http://localhost:5173')
    : win.loadFile(path.join(__dirname, '../frontend/dist/index.html'));
});

app.on('will-quit', () => pythonProcess?.kill());
```

---

## 12. Tailwind Config (design tokens mapped)

```javascript
// tailwind.config.js
module.exports = {
  content: ['./src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        paper:   '#FAFAF8',
        sheet:   '#FFFFFF',
        surface: '#FFFFFF',
        raised:  '#F5F5F4',
        border:  {
          DEFAULT: '#EBEBEA',
          strong:  '#D5D5D3',
        },
        text: {
          primary:   '#0D0D0D',
          secondary: '#3A3A3A',
          muted:     '#666666',
          dim:       '#888888',
          ghost:     '#AAAAAA',
          silent:    '#CCCCCA',
        },
        indigo: {
          DEFAULT: '#4F46E5',
          mid:     '#6366F1',
        },
        alarm:   '#DC2626',
        caution: '#D97706',
        clear:   '#16A34A',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      fontSize: {
        'data-lg': ['26px', { lineHeight: '1', letterSpacing: '-0.05em', fontWeight: '700' }],
        'data-sm': ['10.5px', { lineHeight: '1.4', letterSpacing: '0', fontWeight: '500' }],
        caption:   ['10px',   { lineHeight: '1', letterSpacing: '0.08em', fontWeight: '500' }],
      },
    }
  },
  plugins: [],
}
```

---

## 13. macOS-Specific Notes

- Use `titleBarStyle: 'hiddenInset'` in Electron — gives you native traffic lights without building your own
- Set `backgroundColor: '#FFFFFF'` on BrowserWindow to prevent any white flash (it already matches)
- Register the app as `public.app-category.finance` for App Store submission later
- Set `NSDocumentsFolderUsageDescription` in Info.plist if you access the Documents folder for saving audit logs
- Minimum macOS version for Electron 30+: **macOS 10.15 Catalina**
- For the SQLite audit log, store at `app.getPath('userData')/credexa.db`
- `app.getPath('userData')` on macOS resolves to `~/Library/Application Support/Credexa AI/`

---

## 14. Quick Reference — Design Decisions Rationale

| Decision | Rationale |
|---|---|
| Light-only theme | beminimalist.co's clinical white signals precision and objectivity — the qualities a fraud detection tool must project. Dark terminals signal monitoring; white labs signal analysis. Underwriters reading reports all day are better served by a high-contrast, white reading environment. |
| Warm off-white (`#FAFAF8`) for app background | Pure `#FFFFFF` everywhere creates no depth. The warm paper tone makes white cards float naturally above the background without any box-shadow needed. |
| No box-shadow on cards | On a warm-white background, a 1px `#EBEBEA` border is sufficient to distinguish a white card. Shadows add noise; borders communicate structure cleanly. |
| JetBrains Mono for numbers | Monospace alignment makes risk scores, case IDs, and amounts instantly scannable in a table; Inter for numbers reads poorly when values vary in digit count. |
| 54px icon-only sidebar | Maximizes content area; underwriters are power users who learn the icons; tooltips handle discovery. |
| Semantic color as the ONLY color | On a white interface, the moment a red score appears, it has 100% of the user's attention. If everything else competed for color, risk signals would need to be louder. Restraint multiplies the impact of alarm. |
| No animation on view switch | Speed signal — the app responds instantly. A 150ms fade-in would make it feel slow in a decision-support context. |
| Risk score as arc, not number-only | A number alone requires cognitive parsing; the arc gives a gestalt read in <200ms peripheral vision. |
| Semantic red/amber/green | Universal in financial contexts (RAG status systems); no learning curve for underwriters. Slightly deeper hues (`#DC2626`, `#D97706`, `#16A34A`) than Tailwind defaults for better contrast on white. |
| Tight tracking (-0.05em) on data values | Borrowing from Linear's density aesthetic on a clean white background — signals "this is professional tooling, not a consumer app." |
