# AgenticOS: System Architecture

AgenticOS is a secure, autonomous agentic framework designed for high-performance local and cloud-based operations. This document provides a deep dive into the internal mechanics, orchestration loop, and modular design of the system.

## [ARCH] Core Philosophy
The architecture is built on four pillars:
1.  **Autonomy**: The agent should handle ambiguity and recover from errors without human intervention.
2.  **Safety**: A multi-layered guardrail system protects the host OS from destructive actions.
3.  **Observability**: Every thought, action, and tool output is tracked and logged in real-time.
4.  **Extensibility**: A robust plugin system allows for seamless "Self-Evolution" of tool capabilities.

---

## [SYNC] High-Level Component Overview

```mermaid
graph TD
    User([User Request]) --> Main[main.py]
    Main --> Config[ConfigLoader / Layered YAML]
    Config --> Orchestrator[Runtime Orchestrator]
    Orchestrator --> Agent[Autonomous Agent]
    Agent --> Memory[Session Memory / SQLite]
    Agent --> Registry[Tool Registry]
    Registry --> Files[Filesystem Tools]
    Registry --> Terminal[Terminal & OS Tools]
    Registry --> Web[Web & API Tools]
    Registry --> Browser[Playwright Automation]
    Registry --> Plugins[Dynamic Plugins]
    
    Orchestrator --> UI[Typewriter UI / Notifications]
    Orchestrator --> Guard[PathGuard / Security]
    Guard --> Redact[Secret Redaction Engine]
    Orchestrator --> Test[Pytest / Testing Layer]
```

---

## [LOOP] The Orchestration Loop (Execution Cycle)

AgenticOS follows a strict, iterative "Replan-Act-Verify" loop managed by `core/runtime.py`.

### 0. Configuration Layer
Before the loop starts, the `ConfigLoader` merges multiple YAML sources from the `config/` directory:
- **`runtime.yaml`**: Environment-specific paths and heuristics.
- **`policy.yaml`**: Security rules and redaction patterns.
- **`endpoints.yaml`**: External URLs and service presets.
- **`prompts.yaml`**: System prompts and instruction templates.

### 1. Context Assembly
Before every iteration, the Orchestrator assembles the "Global Context Window":
-   **System Prompt**: Core behavioral instructions and tool definitions.
-   **Session History**: Trimmed and summarized conversation history from SQLite.
-   **Live Metrics**: CPU, RAM, and Disk health snapshots to inform resource-heavy decisions.
-   **Task State**: The current `OBJECTIVE`, `PLAN`, and `CURRENT_STEP`.

### 2. Model Inference
The assembled context is sent to the configured provider (Ollama or Nvidia Cloud). AgenticOS uses a "Reasoning-First" approach, where the model is encouraged to think before generating an `ACTION`.

### 3. Action Dispatching
When the model generates an `ACTION` block, the `ToolRegistry` intercepts it.
-   **Validation**: The tool name and arguments are checked against the registry schema.
-   **Security Check**: The `PathGuard` evaluates any filesystem paths against the Zone-Based security policy.
-   **Dispatch**: If allowed, the tool is executed natively (Python, PowerShell, or Bash).

### 4. Observation & Self-Healing
The tool output (the `OBSERVATION`) is fed back into the model. If a tool fails (e.g., "File not found"), the `Self-Healing` logic kicks in:
-   **Auto-Correction**: The agent identifies the error and attempts a different approach (e.g., searching for the file instead of guessing the path).
-   **Fallback Models**: If the primary model generates invalid JSON, the orchestrator can transparently retry with a secondary, more structured model.

---

## [LOGIC] Memory Management (Long-Term & Short-Term)

### SQLite Backend
Unlike standard chatbots, AgenticOS uses a persistent SQLite database (`data/memory.sqlite3`) to track:
-   **Tool Events**: A full audit log of every tool called and its result.
-   **Artifact Tracking**: A registry of every file created or modified by the agent.
-   **Preference Learning**: User habits and frequent paths are extracted and stored for future runs.

### Summarization Logic
To prevent context window bloat, the agent automatically summarizes the history every 200 messages. This "Compression" ensures that the agent retains critical goal-oriented context while discarding low-value intermediate steps.

---

## [TOOL] Tool Registry & Plugin Architecture

The registry (`core/tool_registry.py`) is the brain of the agent's capabilities. It manages over 180+ tools across several categories.

### Category Breakdown
| Category | Primary Tools | Implementation Type |
| :--- | :--- | :--- |
| **Filesystem** | `read_file`, `write_file`, `grep_dir` | Native Python / pathlib |
| **Terminal** | `run_powershell`, `process_list` | Subprocess / OS APIs |
| **Web** | `web_search`, `fetch_url`, `rss_feed` | HTTP Requests / Scrapers |
| **Automation** | `browser_launch`, `mouse_click` | Playwright / PyAutoGUI |
| **Security** | `eventlog_query`, `system_health` | Windows WMI / EventLog |

### Fast-Disk Audit System
One of the most advanced components of the architecture is the **Fast-Path** optimization. When performing high-load tasks (like scanning the entire `C:` drive), the agent bypasses slow Python-based recursion and utilizes native PowerShell pipelines for near-instant execution.

---

## [SECURE] Security & PathGuard

The architecture enforces a "Zero Trust" model for the local system.
-   **Green Zone (Workspace)**: Full autonomous access for read/write/delete.
-   **Yellow Zone (User Folders)**: Read-only access allowed; Write/Delete requires a **Human-In-The-Middle (HITM)** confirmation.
-   **Red Zone (System)**: Access to critical paths like `C:\Windows` or `C:\Program Files` is strictly blocked by the hardware-level guardrails.
-   **Redaction Engine**: Automatically masks API keys, tokens, and sensitive PII in all logs and memory stores based on regex patterns in `policy.yaml`.

---

## [STATS] Performance Characteristics

| Metric | Target | Real-World Performance |
| :--- | :--- | :--- |
| **UI Latency** | < 10ms | Optimized block-printing removes typewriter lag. |
| **API Resilience** | 100% | Exponential backoff masks all 429 Rate Limit errors. |
| **Startup Time** | < 2s | Hot-reloading enables near-instant initialization. |
| **File Indexing** | 1M files/min | PowerShell optimized scans prevent system lockup. |

---

##  Lifecycle of a Task

1.  **Initialize**: `main.py` loads the `.env` file and `config.yaml`, then starts the `Runtime`.
2.  **Objective**: User provides a prompt; Agent breaks it into a 5-10 step `PLAN`.
3.  **Iterate**: Agent executes tools one by one, updating the `CURRENT_STEP`.
4.  **Verify**: Agent calls `file_exists` or `read_file` to confirm the task is done.
5.  **Finalize**: Agent produces a `FINAL ANSWER` and shuts down cleanly.

---

## [TEST] Hardening & Resilience Checklist
Before deploying AgenticOS in an enterprise environment, ensure the following:
- [ ] `autopilot` is enabled for non-blocking runs.
- [ ] `sqlite` backend is active for persistent artifact tracking.
- [ ] `nvidia` or `gemini` cloud providers are configured for complex reasoning tasks.
- [ ] `PathGuard` is enabled with `require_hitm_outside_workspace: true`.

---

*Last Updated: 2026-05-13*
*Status: Verified Project*
