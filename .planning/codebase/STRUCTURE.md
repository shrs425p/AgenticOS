# Codebase Structure

**Analysis Date:** 2026-06-05

## Directory Layout

```
AgenticOS/
├── assets/             # Documentation logos, banners and assets
├── bin/                # Executable shell wrappers and maintenance scripts
├── config/             # Layered YAML configuration files and templates
├── core/               # Core execution loop, LLM clients, guardrails, memory
│   └── platform/      # OS-specific platform APIs (Windows, macOS, Linux)
├── data/               # Persistent SQLite session databases, local caches
├── docs/               # Technical user manuals, catalogs and guides
├── mock_workspace/     # Sandbox filesystem folders for testing
├── reports/            # Output telemetry reports and status summaries
├── tests/              # Comprehensive test files for unit & integration testing
│   └── integration/   # Long-running integration test cases
├── tools/              # Standard tool implementations (Filesystem, Terminal, Web)
│   ├── filesystem/    # File search, read, write, and audit tools
│   ├── plugins/       # Dynamically loaded user-developed plugin tools
│   ├── terminal/      # Command execution and platform terminal wrappers
│   └── web/           # Scraping, network queries, and browser engines
└── workspace/          # Output folder for user tasks, logs, and artifacts
```

## Directory Purposes

**assets/**
- Purpose: Stores visual assets, logo files, and documentation banners.
- Contains: PNG image files.

**bin/**
- Purpose: Executable shell wrapper scripts for global path registration.
- Contains: Windows batch scripts, shell wrappers, code maintenance helper scripts.
- Key files: `agent` (macOS/Linux script), `agent.bat` (Windows script), `show_history.py` (CLI history parser).

**config/**
- Purpose: Layered configuration declarations overriding default profiles.
- Contains: YAML documents configuring prompts, policies, endpoints, and tool profiles.
- Key files: `prompts.yaml` (system prompt templates), `policy.yaml` (security regulations), `runtime.yaml` (main loop metrics).

**core/**
- Purpose: Foundational engine runtime modules.
- Contains: Python codebase for orchestration, state-machines, rate-limit retry pacing, clients, and memory engines.
- Key files: `runtime.py` (main loop coordinator), `model_clients.py` (LLM clients), `guardrails.py` (PathGuard sandbox), `session_memory_sqlite.py` (SQLite logger).
- Subdirectories: `platform/` - Contains OS-specific APIs for terminal and volume control.

**data/**
- Purpose: System database storage and cache.
- Contains: SQLite databases, cache folders.

**docs/**
- Purpose: Conceptual and manual documentation catalog.
- Contains: Markdown files documenting setup, security policies, and performance.
- Key files: `CATALOG.md` (index of documentation), `architecture.md` (detailed architectural diagrams).

**tests/**
- Purpose: Validation test suite ensuring 100% deterministic capability of modules.
- Contains: Pytest files checking tools, runtime logic, and guardrails.
- Key files: `test_runtime.py` (orchestration checks), `test_guardrails.py` (PathGuard verification).
- Subdirectories: `integration/` - Holds integration suites.

**tools/**
- Purpose: Capabilities registry executed by the orchestrator.
- Contains: Python tool files mapping file, terminal, and browser capabilities.
- Key files: `desktop_notifications.py` (sends desktop alerts), `screen_tools.py` (snapshots desktop).
- Subdirectories: `filesystem/`, `terminal/`, `web/`, `plugins/`.

**workspace/**
- Purpose: Safe directory where the agent runs commands, writes temp files, and places deliverables.
- Contains: Temporary task directories and log outputs.

## Key File Locations

**Entry Points:**
- `main.py` - Core entry point starting bootstrap validation and main execution loop.
- `bin/agent.bat` & `bin/agent` - Script wrappers launching the agent globally.

**Configuration:**
- `config.yaml` - User-facing override configuration.
- `.env` - Environment secret API key variables (gitignored).

**Core Logic:**
- `core/runtime.py` - Manages the Thought-Action-Observation lifecycle loop.
- `core/guardrails.py` - Implements the security sandboxing.
- `core/tool_registry.py` - Dynamic module loading and tool lookup.

**Testing:**
- `tests/` - Directory housing all verification files.
- `pytest.ini` - Base testing configurations.

**Documentation:**
- `README.md` - Primary setup instructions and user manual.
- `docs/CATALOG.md` - Index catalog listing all docs.

## Naming Conventions

**Files:**
- `{name}.py` - Snake-case for all Python files.
- `test_{name}.py` - Prefix for all test runner modules.
- `{name}.yaml` - Configuration profile definitions.
- `{name}.md` - Documentation markdown documents.

**Directories:**
- `{name}` - Snake-case for all directories (e.g. `mock_workspace/`).
- Plural nouns for collections: `tests/`, `tools/`, `assets/`, `reports/`.

**Special Patterns:**
- `__init__.py` - Python package initialization namespaces.
- `__pycache__/` - Dynamic compiled Python bytecode cache (gitignored).

## Where to Add New Code

**New Tool Plugin:**
- Implementation: `tools/plugins/{name}.py` (registered with `@tool` decorator).
- Tests: `tests/test_{name}.py` or testing inline in `tests/test_plugins.py`.

**New Core Feature:**
- Implementation: `core/{name}.py` or integration in `core/runtime.py`.
- Tests: `tests/test_{name}.py`.

**New CLI Script Utility:**
- Implementation: `bin/{name}.py` or standalone shell scripts in `bin/`.

## Special Directories

**venv/**
- Purpose: Local Python virtual environment containing framework dependencies.
- Source: Created by setup scripts (`setup.ps1` / `setup.sh`).
- Committed: No (in `.gitignore`).

---

*Structure analysis: 2026-06-05*
*Update when directory structure changes*
