# MTCB — MEHTYS CODE BRIDGE

> **Privacy-first, developer-focused code translator between Python and JavaScript.**

MTCB is a developer-focused code translation tool designed to translate snippets and single source files cleanly between **Python and JavaScript** in both directions. It supports **Local AI inference via Ollama**, **Cloud AI inference via Google Gemini**, and a deterministic **Mock Translation Engine** for offline test environments.

---

## Features

- **Bidirectional Translation**: Seamless conversion between Python 3 and JavaScript (ES6+).
- **Multi-Provider AI Architecture**:
  - **Google Gemini**: Instant, cloud-powered translation with dynamic model discovery. Defaults to `gemini-3.8-flash` (recommended for coding & high speed) with support for `gemini-3.5-flash-lite`, `gemini-3.1-pro`, and other models available to your key. No local GPU or Ollama daemon required.
  - **Local Ollama**: 100% private, offline inference using `qwen2.5-coder:7b` or custom models.
  - **Mock Engine**: Instant offline structural translation for fast UI verification and testing.
- **Provider Settings Interface**:
  - In-app provider switcher modal with model selection.
  - Password-masked API key input with show/hide toggle.
  - Instant "Test Connection" button (`POST /api/providers/test`) with status feedback.
  - Immediate "Clear API Key" action that purges keys from memory immediately.
  - Explicit data transmission disclosure and mandatory consent checkbox for cloud services.
- **Privacy & Security First**:
  - Untrusted code is **never** evaluated or executed on the client or backend.
  - API keys are held strictly in React runtime memory; they are **never** persisted to `localStorage`, `sessionStorage`, cookies, or disks.
  - Clear visual privacy badges in the UI distinguish **Local &bull; Private** from **Cloud AI &bull; Gemini**.
  - User code and API credentials are never logged to console or backend logs.
  - Ollama offline warnings are shown **only** when Ollama is the active provider.
- **Developer Experience**:
  - CodeMirror 6 split-pane editors with syntax highlighting, line numbers, and drag-and-drop file upload.
  - Custom instruction constraints (e.g., `"use async/await"`, `"prefer arrow functions"`).
  - Detailed explanation card describing idiomatic transformations and warnings.
  - Global `Ctrl+Enter` shortcut to trigger translation from anywhere in the interface.

---

## Project Structure

```text
MTCB/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Header.tsx
│   │   │   ├── StatusBadge.tsx
│   │   │   ├── ProviderSettingsModal.tsx
│   │   │   ├── LanguageSelector.tsx
│   │   │   ├── InstructionsInput.tsx
│   │   │   ├── FileUploader.tsx
│   │   │   ├── CodeEditor.tsx
│   │   │   ├── OutputPanel.tsx
│   │   │   ├── ExplanationCard.tsx
│   │   │   ├── ErrorBanner.tsx
│   │   │   └── editorTheme.ts
│   │   ├── services/
│   │   │   └── api.ts
│   │   ├── types/
│   │   │   └── translation.ts
│   │   ├── App.css
│   │   ├── App.tsx
│   │   ├── index.css
│   │   └── main.tsx
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   └── routes.py
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   └── translation.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── translation_service.py
│   │   │   └── translators/
│   │   │       ├── __init__.py
│   │   │       ├── base.py
│   │   │       ├── gemini.py
│   │   │       ├── mock.py
│   │   │       └── ollama.py
│   │   ├── config.py
│   │   └── main.py
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── test_gemini_provider.py
│   │   ├── test_health.py
│   │   ├── test_mock_translation.py
│   │   ├── test_provider_status.py
│   │   └── test_translation_validation.py
│   ├── requirements.txt
│   └── .env.example
├── docs/
│   └── ARCHITECTURE.md
├── .gitignore
└── README.md
```

---

## Quickstart & Launch Guide (Windows)

### Prerequisites
- Python 3.10+ (tested on Python 3.14)
- Node.js 18+ (tested on Node.js v24)
- [Ollama](https://ollama.com) *(Optional — required only for local offline AI models)*
- Google Gemini API key *(Optional — free keys available at [Google AI Studio](https://aistudio.google.com))*

---

### 1. Backend Setup

Open a PowerShell terminal in the project root:

```powershell
# Navigate to backend directory
cd backend

# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Start FastAPI backend
python -m uvicorn app.main:app --reload --port 8000
```

The backend runs at `http://127.0.0.1:8000`:
- **API Health Check**: `http://localhost:8000/api/health`
- **Provider Status**: `http://localhost:8000/api/providers/status`
- **Test Provider Connection**: `POST http://localhost:8000/api/providers/test`
- **Interactive OpenAPI Documentation**: `http://localhost:8000/docs`

---

### 2. Frontend Setup

In a second PowerShell terminal:

```powershell
# Navigate to frontend directory
cd frontend

# Install npm dependencies
npm install

# Start Vite development server
npm run dev
```

The frontend will open at `http://localhost:5173`.

---

### 3. Choosing Your AI Provider

MTCB gives you total freedom in how translation is executed:

1. **Google Gemini (Cloud AI)**:
   - Click the provider status badge in the header or the **Provider** button in the toolbar.
   - Select **Google Gemini**.
   - Paste your Gemini API key (from [Google AI Studio](https://aistudio.google.com)).
   - Select your preferred model (`gemini-3.8-flash`, `gemini-3.5-flash-lite`, or `gemini-3.1-pro`), or let dynamic discovery load active models.
   - Click **Test Connection** to verify key validity against Google's API catalog.
   - Check the **Consent to transmit code** checkbox.
   - Click **Apply & Use Provider**.
   - *Note: Your key is held only in browser memory and is purged as soon as you close the tab or click "Clear API Key".*

2. **Local Ollama (Offline & Private)**:
   - Install Ollama from [ollama.com](https://ollama.com).
   - Pull the recommended model: `ollama pull qwen2.5-coder:7b`.
   - In MTCB, select **Local Ollama** in Provider Settings.
   - The app communicates directly with `http://localhost:11434`.

3. **Mock Engine (Offline Testing)**:
   - Select **Mock Engine** in Provider Settings.
   - Instant deterministic translations without external network calls or local GPU dependencies.

---

## Running Automated Tests

### Backend Tests (Pytest)
```powershell
.\backend\.venv\Scripts\python -m pytest backend/tests -v
```

All 31 test cases run offline without requiring external network connections or a running Ollama daemon:
- Health and root endpoint verification
- Schema validations (empty code, whitespace rejection, size bounds)
- Provider status check and tag normalization
- Gemini consent requirement validation
- Gemini missing key validation
- Gemini mock-assisted translations (Python &rarr; JS and JS &rarr; Python)
- Gemini rate-limit and quota error mapping
- Dynamic model discovery catalog tests and 404 non-repeating model recommendation tests
- Provider connection test endpoint tests
- Prompt policy adherence tests enforcing Strict Faithful Policy v1.0.0
- Comment, typo, bug, and duplicate preservation regression tests
- Comprehensive 20-item faithful benchmark suite (100.0% measured score)

### Running the Faithful Translation Benchmark Suite
```powershell
.\backend\.venv\Scripts\python -m pytest backend/tests/test_faithful_benchmark.py -v -s
```

### Frontend Build & Typecheck
```powershell
cd frontend
npm run build
```

---

## Security & Privacy Architecture

- **Untrusted Code Is Never Executed**: Code submitted for translation is treated strictly as plain text. Neither client nor backend executes Python or JavaScript snippets.
- **Zero Disk Persistence of Secrets**: User API keys are maintained exclusively in memory in React component state. They are never saved to `localStorage`, `sessionStorage`, indexedDB, cookies, or backend databases.
- **Prominent Purge Control**: Users can instantly clear their API key with one click in the Provider Settings dialog.
- **Explicit Cloud Consent**: Cloud requests to Google Gemini are prevented until the user explicitly checks the data transmission disclosure.
- **Safe Logging**: The FastAPI backend redacts API keys and suppresses full code bodies from application logs.
