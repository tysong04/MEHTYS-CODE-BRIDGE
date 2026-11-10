# MTCB (MEHTYS CODE BRIDGE) — Architecture & Design Specification

## Overview

**MTCB (MEHTYS CODE BRIDGE)** is an open, developer-centric, privacy-first code translation tool designed to perform accurate translations between Python and JavaScript (in both directions). It is built for snippets and single source files, prioritizing local AI execution (via Ollama) so user code is never exposed to third-party cloud APIs.

---

## High-Level System Architecture

```text
┌────────────────────────────────────────────────────────┐
│               Frontend (React 18 + TS + Vite)          │
│   - Split-Pane Editor / Output with Stats & Samples    │
│   - Single-File Uploader (.py / .js with size limits)   │
│   - Live Backend & Provider Status Badges              │
│   - Copy & Download Handlers                           │
└───────────────────────────┬────────────────────────────┘
                            │ HTTP / JSON (REST API)
                            ▼
┌────────────────────────────────────────────────────────┐
│               Backend (Python 3.14 + FastAPI)          │
│   - Input Validation (Pydantic schemas)                │
│   - Safe Logging (code content & secrets redacted)     │
│   - Size & Language Pair Validation                    │
└───────────────────────────┬────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐
│  GeminiProvider   │ │  OllamaProvider   │ │   MockProvider    │
│ - Google REST API │ │ - Local LLM       │ │ - Deterministic   │
│ - Dynamic Catalog │ │ - http://127.0.0.1│ │   offline test    │
│ - gemini-3.8-flash│ │ - qwen2.5-coder   │ │ - Zero setup req  │
└───────────────────┘ └───────────────────┘ └───────────────────┘
```

---

## Modular Provider Interface

All AI translation integrations inherit from `BaseTranslationProvider`:

```python
class BaseTranslationProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Name of provider ('gemini', 'ollama', 'mock')."""
        pass

    @abstractmethod
    async def get_status(self) -> ProviderStatusResponse:
        """Check provider connectivity and model existence."""
        pass

    @abstractmethod
    async def translate(
        self,
        source_lang: Language,
        target_lang: Language,
        code: str,
        instructions: Optional[str] = None
    ) -> TranslationResult:
        """Execute translation between language pair."""
        pass
```

### Providers Implemented:
1. **`GeminiTranslationProvider`**:
   - Communicates with Google's Generative Language REST APIs (`https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`).
   - Dynamic model discovery via `GET https://generativelanguage.googleapis.com/v1beta/models` with API-key-specific catalog filtering for `generateContent`.
   - Defaults to `gemini-3.8-flash`, with support for `gemini-3.5-flash-lite`, `gemini-3.1-pro`, and other models enabled on the user's key.
   - Structured JSON schema enforcement with regex markdown block fallback.
   - Explicit user consent required before sending code to cloud endpoints.
   - Zero credential persistence (keys kept only in client RAM and passed per-request).
2. **`OllamaTranslationProvider`**:
   - Queries Ollama's `/api/tags` endpoint to detect daemon liveness and verify that the target model is installed.
   - Dispatches prompt to `/api/generate` with strict JSON constraints.
   - Parses code, explanations, and warnings, falling back to fence extraction if needed.
   - Never fails silently: returns exact step-by-step shell commands (`ollama pull <model>`) if the service or model is missing.
3. **`MockTranslationProvider`**:
   - Deterministic faithful engine implementing Policy v1.0.0 for automated CI/CD and offline unit testing without requiring GPU or Ollama runtime.
   - String masking preserves quotes, typos, and formatting; indent tracking preserves block structures and emits syntactically valid code.

---

## Strict Faithful Translation Policy (Version 1.0.0)

MTCB prioritizes **faithful translation over code improvement** across all providers and language pairs:
1. **Absolute Translation Policy**: MTCB is a translator, NOT a code fixer, optimizer, refactorer, formatter, or linter. The user's submitted source code is the authoritative source of truth.
2. **Preserve All User-Authored Content**: Exact preservation of comments (typos, punctuation, placement), string literals, identifiers, naming styles, and statement ordering.
3. **Preserve Existing Bugs & Quirks**: Bugs, incorrect conditions (`< 10` instead of `<= 10`), duplicated collection values, and off-by-one errors must remain equivalently incorrect in the target language.
4. **Make Only Necessary Language Adaptations**: Adapt only syntax and idioms required by the target language (`def` ↔ `function`, `print` ↔ `console.log`, `None` ↔ `null`).
5. **Separate Translation from Diagnostics**: Caveats, type mismatches, or detected bugs are reported in `warnings`; `translated_code` is never silently altered.

### Reusable Automated Benchmark Suite
- 20 comprehensive benchmark fixtures spanning 10 distinct categories in both translation directions (Python ↔ JavaScript).
- Evaluates 3 orthogonal dimensions:
  1. **Content Fidelity**: Exact preservation of comments, strings, identifiers, and typos.
  2. **Behavioral Fidelity**: Preservation of logical bugs, conditions, and un-optimized behaviors.
  3. **Target-Language Validity**: Syntactic validity verified via `ast.parse` (Python) and `node --check` (JavaScript).
- Measured benchmark score: **100.0%** across all dimensions (exceeding the ≥ 90.0% requirement).

---

## Security & Privacy Considerations

1. **Zero Untrusted Execution**:
   - Neither the backend nor the frontend ever executes, evals, or compiles user code or translated code.
   - Uploaded files are strictly parsed as raw text.
2. **Data Minimization & Redaction**:
   - Source code snippets and custom instruction prompts are excluded from backend application logs. Only metadata (e.g. byte length, language pair) is logged.
3. **Strict Validation**:
   - Hard limits on code snippet size (64 KB maximum).
   - Validation against empty payloads, identical language pairs, and unsupported language extensions.
4. **No Third-Party Telemetry**:
   - No external trackers, advertising scripts, or remote cloud telemetry.
