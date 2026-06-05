<!-- GSD:project-start source:PROJECT.md -->

## Project

**AgenticOS Security Hardening**

AgenticOS is a secure, high-performance personal AI orchestration framework supporting local and cloud LLMs. This project enhances the zero-trust execution environment of AgenticOS by implementing a robust, AST-like structural command validator to prevent command execution bypasses and obfuscation attacks.

**Core Value:** Ensure 100% reliable detection and blocking of unauthorized shell operations without restricting normal, benign terminal tasks.

### Constraints

- **Compatibility**: Must support both Windows (`cmd`/`powershell`) and Unix/macOS (`bash`) shell execution structures.
- **Performance**: Command parsing and validation must complete in <10ms to avoid degrading loop responsiveness.

<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->

## Technology Stack

## Languages

- Python 3.10+ - All application runtime, core orchestration, tools, and testing code.
- PowerShell 5.1+ - Environment setup and configuration scripts for Windows (`setup.ps1`).
- Bash 3.2+ - Environment setup and configuration scripts for macOS/Linux (`setup.sh`).

## Runtime

- Python 3.10+ virtual environment (`venv`).
- Windows Command Prompt/PowerShell, macOS Terminal, or Linux Bash.
- pip (included in virtual environment)
- Lockfile/dependencies: `requirements.txt` and `requirements-dev.txt` are present.

## Frameworks

- Custom AgenticOS Framework - Private, secure, high-performance personal AI orchestration framework.
- pytest 9.0.3 - Unit and integration testing framework.
- pytest-cov 7.1.0 - Code coverage measurement.
- ruff 0.15.15 - Fast Python linter and formatter.
- black 26.5.1 - Deterministic Python code formatter.
- mypy 2.1.0 - Static type checker for Python.
- radon 6.0.1 - Cyclomatic complexity code analyzer.
- pdoc 16.0.0 - API documentation generator.
- bandit 1.9.4 - Security linter/auditor.

## Key Dependencies

- `google-genai` 2.8.0 - Official client SDK for Google Gemini models.
- `openai` 2.41.0 - Client SDK for OpenAI-compatible APIs (e.g. Nvidia NIM cloud endpoints).
- `groq` 1.4.0 - Client SDK for Groq API endpoint acceleration.
- `playwright` 1.60.0 - Browser automation engine for E2E crawling and page scraping.
- `requests` 2.34.2 & `httpx` 0.28.1 - Synchronous and asynchronous HTTP networking libraries.
- `pyyaml` 6.0.3 - Config parser for YAML configuration files.
- `python-dotenv` 1.2.2 - Parses environment variables from `.env` file.
- `pyautogui` 0.9.54 - Cross-platform GUI control library.
- `psutil` 5.9.8 - Retrieves hardware/process system metrics.
- `Pillow` 12.2.0 - Image processing support.
- `pandas` 2.2.2 & `numpy` 1.26.4 - Data analysis and structural manipulation.
- `matplotlib` 3.10.9 - Data visualization/plotting library.

## Configuration

- Configured via `.env` file (stores secret keys like `NVIDIA_API_KEY`, `GOOGLE_API_KEY`).
- Base environment variables loaded dynamically via `python-dotenv`.
- `pytest.ini` - Pytest runtime configuration.
- `pydoc-markdown.yml` - Configuration for API documentation generator.
- `config.yaml` - Main user settings file overriding core defaults.
- `config/*.yaml` - Layered system configuration directories.

## Platform Requirements

- Cross-platform: Windows 10/11, macOS, or modern Linux.
- Requires Python 3.10+ installed globally.
- Runs locally on developer/operator machines.
- Persistent local SQLite database for session memory.

<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->

## Conventions

## Naming Patterns

- snake_case.py for all Python modules (e.g. `model_clients.py`).
- test_*.py prefix for test files (e.g. `test_runtime.py`).
- UPPERCASE.md for documentation (e.g. `README.md`).
- snake_case for all function and method names (e.g. `get_logger`, `list_models`).
- `_` prefix for private helper functions/methods (e.g. `_load_api_key`).
- snake_case for variable names (e.g. `api_key`, `logger`).
- UPPER_SNAKE_CASE for constants (e.g. `_CACHED_LOG_LEVEL`, `BASE_DIR`).
- PascalCase for class names (e.g. `OllamaClient`, `NvidiaClient`).

## Code Style

- `black` code formatter (26.5.1) - strict Python styling enforcement.
- `ruff` (0.15.15) - code linting and style checking.
- Line length: Standard PEP 8 (88-100 characters max).
- Double quotes preferred for string literals (enforced by `black`).
- Indentation: Strict 4 spaces (no tabs).
- Checked via `ruff check` and static analysis via `mypy`.
- No unused imports, no undeclared variables.
- Run: `ruff check` / `mypy .`

## Import Organization

- Blank lines must separate the three major import categories.
- Alphabetical sorting within each category.

## Error Handling

- Core business logic errors throw specific custom exceptions defined in `core/exceptions.py`.
- Try/except blocks capture expected failures, log warning/error diagnostics, and propagate or return a default placeholder.
- HTTP transient rate limit errors (HTTP 429) are pacing-shielded via `core/retry.py` and converted to `RateLimitExhausted` if the retry limit is breached.
- Failures must be logged using the standard logger before returning or raising.
- Use `logger.exception` to log the full stack trace on unexpected system exceptions.

## Logging

- Centralized logger factory `core.logger.get_logger(__name__)`.
- Levels: debug, info, warning, error, critical.
- Console outputs use simple formatting for readability.
- File logs are fully structured, timestamped, and written to `data/logs/agenticos.log`.
- No raw `print` statements in production core modules.

## Comments

- Comments must explain "why" a design choice was made, especially when integrating with complex API behaviors or platform workarounds (e.g. reconfiguring sys.stdout for Windows Unicode compatibility).
- Document complex logic blocks or optimization pathways.
- Google-style triple-quoted string docstrings are required for all public classes, methods, and functions.
- Specify `Args`, `Returns`, and `Raises` fields explicitly.
- Formatted as `# TODO: description` to track tasks or cleanup targets.

## Function Design

- Keep functions modular and focused. Break large routines into sub-functions.
- Guard clauses at the beginning of functions (return early) to avoid deep nested indentation.
- Limit parameter counts (typically under 4). Use dictionary configurations or configuration objects for complex parameters.

<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->

## Architecture

## Pattern Overview

- Thought-Action-Observation main execution loop.
- Zero-trust security guardrails (PathGuard and Command Sanitizer).
- Local persistent SQLite database for session memory and logs.
- Dynamic plugin system allowing runtime extension of capabilities.
- Exponential backoff rate-limit shielding for cloud APIs.

## Layers

- Purpose: Load configuration profiles, validate environment credentials, and execute boot-time diagnostics.
- Contains: Layered configurations and schema verification.
- Location: `core/runtime_config.py`, `core/config_validator.py`
- Depends on: Standard library YAML parser, `.env` variables.
- Used by: Entry point (`main.py`).
- Purpose: Coordinates execution lifecycle, schedules task resolution, tracks loop iterations, and implements Human-in-the-Loop constraints.
- Contains: Thought processing, command dispatching, and error-recovery logic.
- Location: `core/runtime.py`
- Depends on: Configuration layer, Tool registry, Model clients, Guardrails, Memory.
- Used by: Entry point (`main.py`).
- Purpose: Abstraction layer converting uniform chat payloads into provider-specific API calls.
- Contains: Model adapters (Ollama, Nvidia, Gemini, Groq, OpenAI) and network resilience logic.
- Location: `core/model_clients.py`, `core/retry.py`
- Depends on: `openai`, `google-genai`, `groq`, `requests` packages.
- Used by: Execution Loop (`core/runtime.py`).
- Purpose: Enforces system safety constraints, monitors file access, and blocks malicious command execution.
- Contains: PathGuard security zoning, command regex sanitizers.
- Location: `core/guardrails.py`
- Depends on: Python filesystem libraries.
- Used by: Execution Loop (`core/runtime.py`).
- Purpose: Persists thoughts, action traces, tool outputs, and short/long-term memory.
- Contains: SQLite connection and query wrappers, vector mapping, context engines.
- Location: `core/session_memory_sqlite.py`, `core/memory_manager.py`, `core/context_engine.py`
- Depends on: standard `sqlite3` library.
- Used by: Execution Loop (`core/runtime.py`).
- Purpose: Discovers, validates, registers, and runs modular capabilities (tools and dynamic plugins).
- Contains: Tool registration decorators (`@tool`), dynamic hot-reload routines.
- Location: `core/tool_registry.py`, `core/tool_base.py`
- Depends on: Python import system.
- Used by: Execution Loop (`core/runtime.py`).

## Data Flow

- Persistent SQLite state: All execution traces, metrics, and memory are stored in SQLite database.
- Memory manager: Handles context compaction and retrieval.

## Key Abstractions

- Purpose: Uniform client interface for LLM calls.
- Examples: `OllamaClient`, `NvidiaClient`, `GeminiClient`, `GroqClient` in `core/model_clients.py`.
- Pattern: Adapter Pattern.
- Purpose: Code block executing a specific OS or network action.
- Examples: `tools/filesystem/`, `tools/terminal/`, `tools/web/`.
- Pattern: Command Pattern.
- Purpose: Directory zones boundary controller.
- Location: `core/guardrails.py`.
- Pattern: Gatekeeper / Proxy Pattern.

## Entry Points

- Location: `main.py`
- Triggers: Command line invocation (`python main.py` or command shortcut `agent`).
- Responsibilities: Runs early config validation, handles `--health` checking or `--dream` improvement execution, starts runtime loop.
- Location: `core/runtime.py:main`
- Triggers: Called by `main.py` after bootstrap.
- Responsibilities: Loops requests, handles tools processing, exits when complete.

## Error Handling

- Centralized Exponential Backoff: `core/retry.py` catches API `429 Too Many Requests` rate limit exceptions, executing jittered retries before raising.
- Fail-fast config: Invalid YAML or missing credentials abort booting early inside `core/config_validator.py`.
- Tool execution: Tool exceptions are caught, sanitized, and fed back to the LLM context as standard observations rather than crashing the framework.

## Cross-Cutting Concerns

- Standardized logger factory `core/logger.py` writing console colors and saving logging files under `workspace/logs/agenticos.log`.
- Security audit log persisted in SQLite via `core/audit_logger.py`.
- YAML config validation via `core/config_validator.py`.
- Tool plugin structure validation via `tools/plugin_validator.py`.

<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->

## Project Skills

No project skills found. Add skills to any of: `.agent/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->

## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:

- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->

## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
