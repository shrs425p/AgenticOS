# AgenticOS: Self-Improvement and the Dreaming Engine

This document provides a technical guide to the Self-Improvement ("Dreaming") engine of AgenticOS. This module programmatically reflects on past task executions, analyzes failure modes, and updates the system's long-term memory to continuously optimize future autonomous behaviors.

---

## Architectural Concept

The Self-Improvement engine is driven by the `SelfImprovementDaemon` ([self_improvement.py](../core/self_improvement.py)). Rather than executing tasks in a historical vacuum, the agent conducts a "Dream Cycle" to consolidate experience:

```text
  [Session Start / --dream flag]
                │
                ▼
      [Daemon should_dream?]
                │
        ┌───────┴───────┐
        ▼ (Yes)         ▼ (No: skip)
    [Read History]   [Exit Cycle]
   task_tracking.json
        │
        ▼
   [Filter Tasks]
   ├─ Failures
   └─ Slow tasks (> threshold)
        │
        ├────────────────────────┐
        ▼ (Online Mode)          ▼ (Offline Fallback)
  [LLM Reflection Chat]   [Offline Heuristics Scan]
  Generate lessons learned   ├─ AST parse plugins for docstrings
        │                    └─ Log regex scans for warnings
        │                                │
        └───────────┬────────────────────┘
                    ▼
           [Commit reflections]
           ├─ Append to MEMORY.md
           └─ Write daily_logs/dream_log_*.md
```

---

## The Dreaming Cycle

A dream cycle can be triggered programmatically at the start of a new session or run manually via the command line interface:

### 1. Heuristics Filtering
The daemon reads from `data/memory/task_tracking.json` and loads the history of completed tasks. It prioritizes:
*   **Failures**: Tasks where the success flag is false.
*   **Slow Tasks**: Tasks whose execution duration exceeded the configured slow threshold (default: 120 seconds).
*   **General Context**: If no failures or slow tasks occurred, the daemon selects the most recent tasks up to the configured limit.

### 2. Reflection Engine Modes

#### ◆ A. Online Reflection (LLM-Guided)
If a model client is connected, the daemon formats the target task goals, tools used, durations, and result snippets into a structured history report. It prompts the LLM to extract exactly 3 to 5 highly specific lessons:
*   **Preventative Lessons**: What mistakes occurred and how to avoid them.
*   **Success Patterns**: Which execution paths were most effective and should be repeated.
*   **Environment Insights**: Newly discovered configuration structures, system properties, or user preferences.

#### ◆ B. Offline Fallback Scan
If the model client is offline or rate-limited, the daemon executes a fallback heuristic scan:
*   **AST Plugin Verification**: Uses Python's `ast` module to parse files in `tools/plugins/` and check for functions missing Google-style docstrings (which could cause execution loop model mapping failures).
*   **Log Warning Auditing**: Scans active log files under `data/logs/` for lines containing `ERROR` or `WARNING` and extracts their context.

### 3. Memory Consolidation
Once reflections are compiled, they are written to two persistent storage targets:
*   **System Memory**: Appends a timestamped block to `workspace/MEMORY.md`. This file is injected into the global context window on subsequent session initializations.
*   **Daily Log Archive**: Creates a daily markdown report under `workspace/daily_logs/dream_log_YYYY-MM-DD.md` for developer audit logs.

---

## Configuration Heuristics

The dreaming engine is configured in the layered system YAML configuration files:

```yaml
heuristics:
  # The minimum number of hours required between autonomous dream cycles
  dream_interval_hours: 6

  # The duration threshold in seconds above which a task is classified as slow
  slow_task_threshold_seconds: 120

  # The maximum number of historical tasks included in the reflection payload
  dream_task_limit: 15
```

---

## Manual Execution (CLI)

Developers can trigger a manual dream cycle to audit current tasks and update memory without starting a new loop:

```bash
python main.py --dream
```

To force execution and bypass the 6-hour interval check:
*   Pass the force argument programmatically: `run_dream_cycle(workspace_root, force=True)`.
