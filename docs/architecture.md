<!-- generated-by: gsd-doc-writer -->
# Architecture Overview

## System Overview
AgenticOS is structured as a modular operating system control framework. It decouples task planning, command dispatching, host security, and environment profiling. The framework is designed to run in a loop where the orchestrator receives user intents, queries the model clients for actions, validates those actions against a strict zero-trust sandbox, schedules independent actions in parallel, updates memory contexts with exponential decay filters, and handles errors with transient retry logic.

---

## Component Diagram

```mermaid
graph TD
    Agent[Agent Orchestrator] -->|1. Request Action| FallbackRouter[LLM FallbackRouter]
    Agent -->|2. Check/Run Actions| ParallelScheduler[Parallel Action Scheduler]
    ParallelScheduler -->|3. Security Checks| SafetyMixin[AST & Redirection Guard]
    ParallelScheduler -->|4. Profile Load| ResourceProfiler[Hardware Auto-Tuner]
    ParallelScheduler -->|5. Run Tool| SystemTools[System & Custom Tools]
    Agent -->|6. Save/Resume| CheckpointManager[SQLite Checkpoint Manager]
    Agent -->|7. Episodic Recall| VectorMemory[FAISS Vector Memory]
```

---

## Data Flow

A typical task execution flow proceeds as follows:
1. **Startup Profiling**: The `ResourceProfiler` executes psutil checks to identify the system CPU/RAM tier. It dynamically overrides worker and context limits in the `ParallelScheduler` and `ContextEngine`.
2. **Intent & Checkpoint Check**: The orchestrator checks if a persistent checkpoint exists for the goal using the `CheckpointManager`. If found, it resumes execution from the first incomplete phase.
3. **Prompt Formulation**: The orchestrator queries the `VectorMemory` for semantically similar historical actions (weighted by a 30-day half-life decay) and constructs the prompt using model-specific templates.
4. **Action Generation**: The model client returns streaming actions which are parsed incrementally by the `StreamingActionParser`.
5. **Security Validation**: Prior to execution, each command token is intercepted by the `SafetyMixin` AST validator to check for character escape obfuscation or unauthorized write redirects.
6. **Parallel Execution**: Independent actions are grouped into execution waves by the `ParallelScheduler` and run concurrently in thread pools.
7. **Resilience & Stall Checks**: Tool execution times are evaluated by the `StallMonitor`. If an error occurs, the `RetryClassifier` decides whether to retry (transient locks/timeout) or abort (permissions/syntax).
8. **Goal Verification**: Prior to final response, the `SuccessCriteria` parser confirms all user-specified criteria are satisfied.

---

## Key Abstractions

- **`Agent`** ([`core/orchestrator.py`](file:///c:/Users/pawar/AgenticOS/core/orchestrator.py)): Main loop controller managing context window limits, prompt assembly, validation gates, and checkpoint states.
- **`ParallelScheduler`** ([`core/dispatcher.py`](file:///c:/Users/pawar/AgenticOS/core/dispatcher.py)): Resolves action dependency graphs using Kahn's topological sort and executes independent tools concurrently in thread pools.
- **`FallbackRouter`** ([`core/model_clients.py`](file:///c:/Users/pawar/AgenticOS/core/model_clients.py)): Standardizes fallback routing across local and cloud providers, cascading requests during rate limits or token exhaustion.
- **`PathGuard`** ([`core/guardrails.py`](file:///c:/Users/pawar/AgenticOS/core/guardrails.py)): Validates symlink depth and traversal bounds to isolate filesystem writes to approved workspaces.
- **`CheckpointManager`** ([`core/checkpoint_manager.py`](file:///c:/Users/pawar/AgenticOS/core/checkpoint_manager.py)): Dual-persists multi-session agent phase checklists to local JSON and SQLite.
- **`VectorMemory`** ([`tools/plugins/vector_memory.py`](file:///c:/Users/pawar/AgenticOS/tools/plugins/vector_memory.py)): Performs FAISS vector matching, applies time-decay weights, and retrieves verified evidence.

---

## Directory Structure Rationale

- `core/`: High-performance core framework (orchestrator, scheduler, config, profiler, and clients).
- `tools/`: Built-in OS automation tools.
  - `tools/platform/`: OS-specific native UI backend dispatchers (Windows COM, macOS AppleScript, Linux screenshots).
  - `tools/terminal/`: Local terminal execution utilities and AST safety mixers.
  - `tools/plugins/`: Dynamically registered custom tools and plugins (e.g. vector memory, log analyzers, etc.).
- `docs/`: User and onboarding documentation.
- `tests/`: Integrated test suites, mutation harnesses, and E2E simulation setups.
