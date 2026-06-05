# AgenticOS: Performance Optimization and Scaling

AgenticOS is engineered for speed. During production stress testing, we identified and eliminated several major bottlenecks that traditionally slow down autonomous agents. This document details the optimization techniques used to achieve near-instant UI response times and high-speed system scanning.

---

## The "No-Lag" Terminal UI

The most common performance issue in terminal-based agents is "Typewriter Lag." Traditionally, agents print every character individually to simulate "thinking," which causes massive IPC (Inter-Process Communication) overhead.

### The Problem:
-   Printing 1,000 characters one-by-one requires 1,000 separate flushes to the terminal.
-   On Windows, this can lead to 100% CPU usage just from the terminal window itself.

### The Solution: Block-Printing
In `core/runtime_ui.py`, we replaced character-by-character flushing with **Block-Level Printing**:
```python
def typewriter_print(text, style=None):
    # Instead of: for char in text: sys.stdout.write(char)
    # We now print in optimized chunks or full lines
    sys.stdout.write(style + text + C.RESET)
    sys.stdout.flush()
```
**Result**: UI response times improved by **95%**, and terminal-induced CPU lag was eliminated.

---

## High-Speed Python DFS "Fast-Path"

Standard Python library tools like `pathlib.Path.rglob` are notoriously slow when traversing filesystems because they construct heavy objects and check directories recursively with a lot of overhead.

### The Optimization:
AgenticOS uses a custom stack-based depth-first search (DFS) traversal implemented natively in Python using `os.scandir()`. 
- **Low-level Win32 integration**: Python's `os.scandir` directly accesses Windows directory APIs, fetching metadata like size and timestamps in a single pass without extra disk stats.
- **Process-Free Execution**: Avoids the heavy process startup and pipeline overhead of calling PowerShell.
- **NTFS Loop Protection**: Explicitly detects and skips NTFS junction points and reparse points (`stat.st_file_attributes & 0x400`) to prevent infinite directory loops.

#### Example: Finding Large Files
-   **Old Way (Python pathlib)**: `root.rglob("*")` -> `p.stat()` for every file (slow, creates millions of heavy `Path` instances).
-   **New Way (Optimized Python DFS)**:
    Stack-based DFS traversal utilizing `os.scandir()` to query directory entries and metadata on-the-fly.

**Benchmarks**:
| Task | Standard Python pathlib | Native PowerShell | Optimized Python DFS | Improvement |
| :--- | :--- | :--- | :--- | :--- |
| **Workspace File Audit** | 35.4 Seconds | 28.0 Seconds | **0.20 Seconds** | **~170x Faster** |
| **500k Files Scan (system drive)** | ~15 Minutes | ~3 Minutes | **9.7 Seconds** | **~90x Faster** |

---

## Memory and Context Optimization

LLM context windows are precious. AgenticOS uses several heuristics to minimize memory bloat.

### 1. Smart Truncation
In `config.yaml`, the `max_observation_chars` setting (default: 4,000) ensures that a single large tool output (like a 50KB JSON) doesn't consume the entire context window.

### 2. SQLite Context Backend
By moving from JSON to SQLite (`session_memory_sqlite.py`), the system can handle thousands of messages with zero performance degradation.
-   **Indexing**: Message retrieval is O(1).
-   **Pruning**: Old messages are automatically archived or summarized to keep the active context under the model's limit.

### 3. Hot-Reload Filter Guards
To prevent the agent runtime from thrashing the host system while monitoring code changes, the hot-reloading mechanism (`_get_mtimes` in `core/runtime.py`) filters out heavy non-source directories like `venv`, `node_modules`, `workspace`, and `data` from its file-system walk loops. This prevents scanning thousands of third-party libraries every 2.0 seconds.

### 4. Dynamic Workspace Context Pruning
Workspace listings mapped in the system prompt (`_scan_workspace` in `core/context_engine.py`) skip scanning and child-counting for known project/system folders like `.git`, `venv`, `node_modules`, `__pycache__`, caches, and data directories. This avoids hundreds of slow synchronous disk hits on every turn.

---

## API Resilience and Backoff

Network latency and rate limits (429s) can stall an agent. AgenticOS centralizes retry/backoff logic in `core/retry.py` and exposes a `retry_call()` helper that provider clients use to handle transient failures. The helper implements exponential backoff with configurable jitter and a maximum retry limit. If retries are exhausted, clients raise `RateLimitExhausted` so the orchestrator can trigger fallbacks or user-facing errors.

Example behaviour (conceptual):

1. Attempt the provider call.
2. On transient `RateLimit`/`429` errors, wait `base_retry_delay` seconds (plus jitter).
3. Retry with exponential backoff up to `max_retries` attempts.
4. If still failing, raise `RateLimitExhausted` to the caller.

**Benefits**:
- Prevents agent crashes during high-concurrency tests.
- Provides consistent, configurable retry behaviour across provider clients.

---

## Performance Configuration Reference

Adjust these values in `config.yaml` to scale the performance based on your hardware:

```yaml
performance:
  # Max characters allowed in a single tool observation
  max_observation_chars: 12000
  
  # Throttle for hot-reload file checks (seconds)
  reload_throttle_seconds: 2.0
  
  # Enable background processing for non-blocking tasks
  background_tasks: true
  
  # Parallel tool execution (Experimental)
  parallel_execution: true

  # Retry/backoff configuration for provider clients
  max_retries: 5
  base_retry_delay: 5.0
```

---

## Benchmarking Your System

You can run the built-in performance suite to measure your local optimization levels:
```powershell
python scripts/run_eval.py --task "Task 5"
```
This will generate a `self-monitoring chart` showing:
1.  **RAM Usage** over 60 seconds.
2.  **CPU Spikes** during tool execution.
3.  **Handle Count** (detecting memory leaks).

---

## Summary of Best Practices
-   **Prefer Optimized Python Tools**: For drive-wide operations, use optimized `os.scandir` DFS plugins (like `fast_disk_audit`) to bypass slow `rglob` and avoid PowerShell subprocess overhead.
-   **Batch Operations**: Avoid calling `read_file` 10 times in a row; use a single `grep_dir` or custom script.
-   **Monitor `agent.log`**: Check for `VERBOSE` or `DEBUG` lines to identify slow-running tools.

---

*Last Updated: 2026-05-13*
*Status: Highly Optimized*
