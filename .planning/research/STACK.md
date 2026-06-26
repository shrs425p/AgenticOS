# Stack Research

**Domain:** Agentic OS Control and Development Framework
**Researched:** 2026-06-26
**Confidence:** HIGH

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.11+ | Main execution environment and runtime engine. | Standard for agent frameworks; excellent AST processing; native OS API bindings. |
| SQLite | 3.x | Persistent store for session history and memory tracking. | Lightweight, serverless, atomic, and embedded in Python standard library. |
| Pydantic | 2.x | Configuration validation and action schemas. | High-performance data validation; native JSON schema generation; type-safety. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| FAISS | 1.8+ | Fast vector database for semantic memory lookups. | Used to implement dense vector queries on agent execution logs. |
| sentence-transformers | 3.x | Generating embeddings for vector memory. | Used to embed memories and task queries locally without API calls. |
| pytest-mutagen | 1.x | Mutation testing for test quality analysis. | Used in test suites to verify that tests successfully detect code changes. |
| aiohttp | 3.9+ | Asynchronous HTTP requests and streaming. | Used for async tool executions and streaming large responses. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| grim / slurp | Wayland Linux screenshot utility. | Required because standard X11 screenshot tools fail on Wayland desktops. |
| AppleScript | macOS window and UI control. | Used to click menu bars and list open windows via macOS System Events. |

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| SQLite | PostgreSQL | Multi-tenant deployments requiring concurrent write locks across multiple nodes. |
| FAISS | ChromaDB / Qdrant | If memory indexing needs to scale beyond local memory and require persistence over network. |
| Python native AST | Bash regex | Never recommended for safety; shell injection risk is too high. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| X11 screenshot tools | Fail silently on modern Wayland desktop sessions. | `grim` / `slurp` for Wayland support. |
| Plain dictionary state | Lacks run-time type safety; prone to spelling errors and structural drifts. | Pydantic Models. |
| Subprocess shell=True | Vulnerable to shell injections; lacks tokenization controls. | `subprocess.run` with list of arguments. |

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| Pydantic v2 | Python 3.11+ | Better performance and validation speed. |
| FAISS-cpu | sentence-transformers | Avoids GPU overhead for light local search workloads. |

## Sources

- Official GSD Settings & Templates — Core GSD specifications.
- AgenticOS Codebase Analysis — Structural constraints of the current repository.
