# AgenticOS Core Runtime Engine

The `kernel/` directory contains the foundational systems that drive AgenticOS: the execution loop, model interfaces, security guardrails, configuration validations, persistent memory management, and terminal UIs.

---

## Architectural Blueprint

The runtime architecture of AgenticOS follows a highly coupled, zero-trust lifecycle:

```mermaid
graph TD
    Config[kernel/settings.py] -->|Validate YAML| Validator[kernel/lint.py]
    Validator -->|Initialize Runtime| Runtime[kernel/cli.py]
    Runtime -->|Load Tools| Registry[kernel/registry.py]
    Runtime -->|Check Paths & Commands| Guardrails[kernel/guard.py]
    Runtime -->|LLM Queries| Clients[kernel/models.py]
    Runtime -->|Log and Persist| SQLite[kernel/store.py]
    Clients -->|Exponential Backoff| Retry[kernel/retry.py]
    Registry -->|Execute System Tools| Tools[ops/ & plugins/]
```

---

## Key Subsystems & Modules

### 1. Agent Execution Loop (`kernel/cli.py`)
The central coordinator of AgenticOS. It manages the agent's main thought-action-observation loop:
- **Iteration Tracking**: Enforces hard loop limits to prevent infinite recursion or cost overruns.
- **Human-In-The-Loop**: Pauses execution and requests interactive operator permission for destructive commands or Yellow Zone filesystem operations.
- **Self-Correction & Fallbacks**: Dynamically changes provider endpoints or LLM configurations if repeated errors or empty loops occur.

### 2. Provider API Clients (`kernel/models.py` & `kernel/retry.py`)
An abstraction layer for cloud and local LLM backends (Gemini, Groq, Nvidia, OpenAI, Ollama, OpenRouter).
- **Exponential Backoff**: Integrated with `kernel/retry.py` using standard exponential backoff and jittered retries to elegantly handle HTTP 429 (Rate Limit) errors.
- **Payload Redaction**: Automatically filters system and user credentials before transmitting payloads to external clouds.

### 3. Zero-Trust Security (`kernel/guard.py`)
Enforces safe and compliant filesystem boundaries:
- **PathGuard**: Restricts file modifications based on zones (Green: unrestricted `workspace/`; Yellow: HITM-required system paths; Red: fully blocked operating system zones; Blue: read-only mode). It also protects sensitive workspace internals like `.git` and `.env` files.

### 4. Registry & Plugins (`kernel/registry.py` & `kernel/base.py`)
Loads, parses, and dynamically registers all workspace capabilities:
- **Namespace Reuse**: Reuses cached modules inside `sys.modules` to prevent import collisions and mock leaks in testing environments.
- **Dynamic hot-reloads**: Automatically registers new modules and ops decorated with `@tool` without system reboots.

### 5. Persistent Session Memory (`kernel/store.py`)
Maintains agent state across tasks and system reboots:
- **SQLite Engine**: Stores task definitions, intermediate agent thoughts, ops called, and result payloads.
- **Analytics Database**: Provides an audit trail for performance metrics and regression analysis.

---

## Core File Reference

| Module Name | High-Level Responsibility | Category |
| :--- | :--- | :--- |
| [runtime.py](runtime.py) | Coordinates the main execution loop and schedules task resolution. | Loop |
| [model_clients.py](model_clients.py) | Abstraction layer for Gemini, Groq, Nvidia, and OpenAI API calls. | Model |
| [guardrails.py](guardrails.py) | Implements PathGuard directory isolation rules and sensitive path checks. | Security |
| [session_memory_sqlite.py](session_memory_sqlite.py) | Persists tool invocation history and agent thoughts to SQLite. | Memory |
| [tool_registry.py](tool_registry.py) | Discovers, imports, and exposes standard modules and dynamic plugins. | Extensibility |
| [retry.py](retry.py) | Provides centralized exponential backoff and jittered retries. | Network |
| [cfg_validator.py](cfg_validator.py) | Ensures the integrity of YAML files and system credentials. | Config |
| [runtime_ui.py](runtime_ui.py) | Manages terminal output formatting and typewriter printing. | Interface |

---

## Development Philosophy

The `kernel/` package is strictly isolated from application-specific business logic. It handles the raw plumclig of the agent framework, ensuring that security, memory persistence, API communication, and command execution are completely robust and predictable.
