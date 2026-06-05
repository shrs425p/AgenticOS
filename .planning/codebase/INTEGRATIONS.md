# External Integrations

**Analysis Date:** 2026-06-05

## APIs & External Services

**Nvidia NIM API:**
- Service: Cloud hosting for large language models (e.g. `openai/gpt-oss-120b`).
  - SDK/Client: `openai` Python package v2.41.0 (`NvidiaClient` in `core/model_clients.py`).
  - Auth: API key stored in `NVIDIA_API_KEY` env var.
  - Endpoints: chat completions (`https://integrate.api.nvidia.com/v1`).

**Google Gemini API:**
- Service: Cloud hosting for Google Gemini model range.
  - SDK/Client: `google-genai` Python package v2.8.0 (`GeminiClient` in `core/model_clients.py`).
  - Auth: API key stored in `GEMINI_API_KEY` env var.
  - Endpoints: Gemini generation model endpoints (`generate_content_stream` & `generate_content`).

**Groq API:**
- Service: Groq accelerator cloud endpoint for fast inference.
  - SDK/Client: `groq` Python package v1.4.0 (`GroqClient` in `core/model_clients.py`).
  - Auth: API key stored in `GROQ_API_KEY` env var.
  - Endpoints: chat completions (`llama3-70b-8192` or other default model).

**Ollama Local API:**
- Service: Local runner for open-weight LLMs (defaults to `http://localhost:11434`).
  - SDK/Client: `requests` library for REST calls (`OllamaClient` in `core/model_clients.py`).
  - Auth: None (runs locally).
  - Endpoints: `/api/chat`, `/api/tags`.

**OpenAI Compatible APIs (OpenAI, OpenRouter, DeepSeek, GitHub Models):**
- Service: Various model host APIs utilizing standard OpenAI-compliant routes.
  - SDK/Client: `openai` Python package v2.41.0 (`OpenAICompatibleClient` in `core/model_clients.py`).
  - Auth: Environment variable keys (e.g. `OPENAI_API_KEY`, `OPENROUTER_API_KEY`, `DEEPSEEK_API_KEY`, `GITHUB_TOKEN`).
  - Endpoints: Chat completions base URLs configured via `config/providers.yaml`.

## Data Storage

**Databases:**
- SQLite - Local database for session logs, audit records, and persistent memory.
  - Connection: Local filesystem path.
  - Client: Python built-in `sqlite3` driver (`core/session_memory_sqlite.py`).
  - Storage location: Dynamic path inside `workspace/` or `data/` directories.

**File Storage:**
- Local Filesystem - Workspaces, cache folders, and output files.
  - Client: Python built-in `os` and `shutil` modules.
  - Path Safeguard: Hardware/path-level zone guardrails (`core/guardrails.py`) to restrict file operations within authorized directories.

## Authentication & Identity

**Provider Auth:**
- Token/API Key configuration for each external model service provider.
  - Implementation: Loaded from `.env` file via `python-dotenv` at startup.
  - Secret keys: `NVIDIA_API_KEY`, `GEMINI_API_KEY`, `GROQ_API_KEY`, `OPENAI_API_KEY`, `OPENROUTER_API_KEY`, `GITHUB_TOKEN`.

## Monitoring & Observability

**Logs:**
- Custom Logger - Structured logger factory using standard Python logging.
  - Output: Logs written to console and persisted in `workspace/logs/agenticos.log` or `data/logs/agenticos.log`.
  - Config: Controlled via `log_level` in `config.yaml`.

**Audit Logs:**
- SQLite/JSONL Audit Tracker - Session audit records logging every tool action.
  - Client: `core/audit_logger.py`.
  - Output: sqlite database or JSONL format.

## CI/CD & Deployment

**CI Pipeline:**
- GitHub Actions - Code linting, type-checking, safety, and testing.
  - Workflows:
    - `.github/workflows/ci.yml` - Pytest, black, ruff, mypy, radon, bandit checks.
    - `.github/workflows/bandit.yml` - Security scanning.
    - `.github/workflows/codeql.yml` - CodeQL analysis.
    - `.github/workflows/stale.yml` - Manage stale issues.
    - `.github/workflows/summary.yml` - Workflow summary action.
    - `.github/workflows/ai-middleman.yml` - Workflow middleman runner.

## Environment Configuration

**Development:**
- Required env vars: `NVIDIA_API_KEY` (or `GEMINI_API_KEY`, etc. depending on active provider).
- Secrets location: Local `.env` file (gitignored).

**Production:**
- Runs on client workstation with local environment variables.

---

*Integration audit: 2026-06-05*
*Update when adding/removing external services*
