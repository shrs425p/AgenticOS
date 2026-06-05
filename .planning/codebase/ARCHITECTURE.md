# Architecture

**Analysis Date:** 2026-06-05

## Pattern Overview

**Overall:** Coupled Zero-Trust Autonomous Execution Loop with Extensible Tool Registry.

**Key Characteristics:**
- Thought-Action-Observation main execution loop.
- Zero-trust security guardrails (PathGuard and Command Sanitizer).
- Local persistent SQLite database for session memory and logs.
- Dynamic plugin system allowing runtime extension of capabilities.
- Exponential backoff rate-limit shielding for cloud APIs.

## Layers

**Configuration & Bootstrapping Layer:**
- Purpose: Load configuration profiles, validate environment credentials, and execute boot-time diagnostics.
- Contains: Layered configurations and schema verification.
- Location: `core/runtime_config.py`, `core/config_validator.py`
- Depends on: Standard library YAML parser, `.env` variables.
- Used by: Entry point (`main.py`).

**Execution Loop (Orchestration) Layer:**
- Purpose: Coordinates execution lifecycle, schedules task resolution, tracks loop iterations, and implements Human-in-the-Loop constraints.
- Contains: Thought processing, command dispatching, and error-recovery logic.
- Location: `core/runtime.py`
- Depends on: Configuration layer, Tool registry, Model clients, Guardrails, Memory.
- Used by: Entry point (`main.py`).

**Model Interface Layer:**
- Purpose: Abstraction layer converting uniform chat payloads into provider-specific API calls.
- Contains: Model adapters (Ollama, Nvidia, Gemini, Groq, OpenAI) and network resilience logic.
- Location: `core/model_clients.py`, `core/retry.py`
- Depends on: `openai`, `google-genai`, `groq`, `requests` packages.
- Used by: Execution Loop (`core/runtime.py`).

**Security & Protection Layer:**
- Purpose: Enforces system safety constraints, monitors file access, and blocks malicious command execution.
- Contains: PathGuard security zoning, command regex sanitizers.
- Location: `core/guardrails.py`
- Depends on: Python filesystem libraries.
- Used by: Execution Loop (`core/runtime.py`).

**Storage & Memory Layer:**
- Purpose: Persists thoughts, action traces, tool outputs, and short/long-term memory.
- Contains: SQLite connection and query wrappers, vector mapping, context engines.
- Location: `core/session_memory_sqlite.py`, `core/memory_manager.py`, `core/context_engine.py`
- Depends on: standard `sqlite3` library.
- Used by: Execution Loop (`core/runtime.py`).

**Extensibility (Tool Registry) Layer:**
- Purpose: Discovers, validates, registers, and runs modular capabilities (tools and dynamic plugins).
- Contains: Tool registration decorators (`@tool`), dynamic hot-reload routines.
- Location: `core/tool_registry.py`, `core/tool_base.py`
- Depends on: Python import system.
- Used by: Execution Loop (`core/runtime.py`).

## Data Flow

**AgenticOS Task Execution:**

1. **Boot**: User runs `main.py` (or uses globally registered `agent` command).
2. **Setup**: Configuration is validated; workspace folders, SQLite connection, and tools registry are initialized.
3. **Prompt**: The orchestrator asks the active LLM client adapter (e.g. `GeminiClient` in `core/model_clients.py`) for the next step.
4. **Guard**: If the model decides to run a tool, the request is intercepted by `core/guardrails.py` for zone checking.
5. **Prompt Human**: If the tool modifies a Yellow Zone file, execution is paused for operator approval.
6. **Action**: The tool executes in the registered module (`tools/` or `tools/plugins/`).
7. **Persist**: Thoughts, arguments, and outcomes are persisted in `core/session_memory_sqlite.py`.
8. **Loop**: The cycle repeats until the goal is achieved or iteration limits are hit.

**State Management:**
- Persistent SQLite state: All execution traces, metrics, and memory are stored in SQLite database.
- Memory manager: Handles context compaction and retrieval.

## Key Abstractions

**ModelClient:**
- Purpose: Uniform client interface for LLM calls.
- Examples: `OllamaClient`, `NvidiaClient`, `GeminiClient`, `GroqClient` in `core/model_clients.py`.
- Pattern: Adapter Pattern.

**Tool:**
- Purpose: Code block executing a specific OS or network action.
- Examples: `tools/filesystem/`, `tools/terminal/`, `tools/web/`.
- Pattern: Command Pattern.

**PathGuard:**
- Purpose: Directory zones boundary controller.
- Location: `core/guardrails.py`.
- Pattern: Gatekeeper / Proxy Pattern.

## Entry Points

**CLI Entry Point:**
- Location: `main.py`
- Triggers: Command line invocation (`python main.py` or command shortcut `agent`).
- Responsibilities: Runs early config validation, handles `--health` checking or `--dream` improvement execution, starts runtime loop.

**Core Orchestrator Entry Point:**
- Location: `core/runtime.py:main`
- Triggers: Called by `main.py` after bootstrap.
- Responsibilities: Loops requests, handles tools processing, exits when complete.

## Error Handling

**Strategy:** Centralized retry logic, uniform exceptions, fail-safe fallbacks.

**Patterns:**
- Centralized Exponential Backoff: `core/retry.py` catches API `429 Too Many Requests` rate limit exceptions, executing jittered retries before raising.
- Fail-fast config: Invalid YAML or missing credentials abort booting early inside `core/config_validator.py`.
- Tool execution: Tool exceptions are caught, sanitized, and fed back to the LLM context as standard observations rather than crashing the framework.

## Cross-Cutting Concerns

**Logging:**
- Standardized logger factory `core/logger.py` writing console colors and saving logging files under `workspace/logs/agenticos.log`.

**Audit Logs:**
- Security audit log persisted in SQLite via `core/audit_logger.py`.

**Validation:**
- YAML config validation via `core/config_validator.py`.
- Tool plugin structure validation via `tools/plugin_validator.py`.

---

*Architecture analysis: 2026-06-05*
*Update when major patterns change*
