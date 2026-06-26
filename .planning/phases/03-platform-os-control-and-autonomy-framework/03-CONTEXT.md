---
phase: 3
phase_name: Platform OS Control and Autonomy Framework
slug: 03-platform-os-control-and-autonomy-framework
date: 2026-06-26
status: context_gathered
requirements: [OS-01, OS-02, OS-03, AUTO-01, AUTO-02, AUTO-03, AUTO-04, AUTO-05, DOC-01]
---

# Phase 3 Context: Platform OS Control and Autonomy Framework

## Domain

This phase delivers three related capability clusters:

1. **Native OS UI control** — the agent can perceive and interact with desktop GUIs on Windows, macOS, and Linux without relying solely on terminal commands
2. **Hardware-aware self-tuning** — the agent profiles the host machine at startup and adapts concurrency, context size, and cache thresholds dynamically
3. **Autonomous task resilience** — smart retry/stall/success-criteria logic that makes multi-step tasks complete reliably across sessions and transient failures

---

## Decisions

### macOS UI Control (OS-01)

- **Mechanism**: AppleScript via `osascript` subprocess for menu clicks, window listing, and window focus (zero deps). Optional `pyobjc` for deep Cocoa accessibility element traversal — loaded only when element-level inspection/click/type is needed. `pyobjc` is an optional dep (not in base `requirements.txt`).
- **Scope**: Full UI automation — window list, window focus, menu clicks, UI element inspection (read button/text labels), click into UI elements, type into UI elements.
- **Accessibility permissions**: When the agent lacks macOS Accessibility permissions (disabled in System Settings → Privacy & Security → Accessibility), auto-prompt the user to grant them with clear instructions and retry after confirmation.
- **New file**: `tools/platform/macos_ui.py` — wraps `osascript` calls and optional pyobjc bindings behind a unified interface.

### Linux Desktop Detection & Screenshots (OS-02)

- **Detection strategy**: Env-var primary — read `$XDG_SESSION_TYPE`, `$WAYLAND_DISPLAY`, `$DISPLAY`, `$XDG_CURRENT_DESKTOP` at startup. Runtime probe fallback (attempt Wayland socket connect) when env vars are absent or ambiguous.
- **Screenshot capture**: `grim` + `slurp` for Wayland sessions; `scrot` for X11 sessions — both via subprocess. Agent checks for tool existence with `shutil.which()` and raises a clear `AgentError` with install instructions if missing (rather than failing silently).
- **New file**: `tools/platform/linux_desktop.py` — detection + screenshot dispatch.

### Windows UI Control (Windows-first platform)

- **Mechanism**: `pywin32` / `win32api` — window enumeration (`EnumWindows`), window focus (`SetForegroundWindow`), mouse click (`SetCursorPos` + `mouse_event`), keyboard input (`SendInput`).
- **Scope**: Window list, window focus, click, type — equivalent to macOS scope.
- **Dependency**: `pywin32` already implicitly available on Windows (added to `requirements.txt` if not already present).
- **New file**: `tools/platform/windows_ui.py`.

### Unified Platform API

- **New file**: `tools/platform/__init__.py` — platform dispatcher that detects OS via `sys.platform` / `platform.system()` and routes to the correct backend (`macos_ui`, `linux_desktop`, `windows_ui`).
- `core/platform_api.py` is the existing stub — extend or replace with the new dispatched tools.

### Hardware Auto-Tuning (OS-03)

- **Timing**: Startup profile (once at agent init via `psutil`) + dynamic throttle (re-check every 60s during long tasks; reduce workers/context if available RAM drops below 20% of total).
- **Parameters tuned**:
  - `num_ctx` / `max_tokens` — context window size (Ollama and cloud API clients)
  - `max_workers` — `ThreadPoolExecutor` worker count in `ParallelScheduler`
  - Disk cache size — for web fetch and downloaded content
  - `compact_history` threshold — trigger at lower % of limit on low-RAM machines
- **Tiers** (based on total RAM):
  - Low (≤4 GB): conservative — small context, 2 workers, aggressive compaction
  - Mid (4–16 GB): balanced — default config values
  - High (>16 GB): performance — large context, max workers from CPU count
- **New file**: `core/resource_profiler.py` — profiles hardware and returns a `HardwareProfile` dataclass used to configure the other subsystems at init.

### Multi-Session Checkpoints (AUTO-04)

- **Storage**: JSON primary (`workspace/.checkpoints/<task_id>.json`) for fast writes; SQLite secondary (`session_memory_sqlite.py` backend) for cross-session query/lookup.
- **Schema**: Linear phase list — `{task_id, goal, phases: [{name, status: pending|running|complete, steps: [...], result}], created_at, updated_at}`. Resume from the first phase with `status != complete`.
- **Integration**: `core/task_tracker.py` extended to write/read checkpoint files. Agent checks for an existing checkpoint at task start (by hashing the goal) and offers to resume.
- **New file**: `core/checkpoint_manager.py`.

### Retry & Stall Classifier (AUTO-01, AUTO-03, AUTO-05)

- **Relationship to existing loop guard**: **Parallel, different responsibilities.**
  - `repeated_action_count` (existing) = loop guard — blocks identical action signatures
  - New classifier = error routing — classifies whether to retry, escalate, or abandon
- **Transient vs permanent classification**: Hybrid approach — exit code primary, error-message pattern fallback:
  - Transient keywords: `timeout`, `network`, `connection reset`, `locked`, `temporarily`, `retry`, `503`, `429`, `ETIMEDOUT`, `ECONNREFUSED`
  - Permanent keywords: `permission denied`, `not found`, `syntax error`, `invalid argument`, `ENOENT`, `EPERM`, `EACCES`
  - Default (ambiguous): treat as transient for first 2 retries, then escalate to user
- **Stall detection**: Command-type thresholds (file ops: 30s, network: 60s, package installs: 300s, general: 120s). When elapsed time exceeds threshold, emit a stall warning and suggest a faster alternative from a lookup table.
- **Faster-alternative lookup table** (AUTO-05): e.g. large file copy → archive first; full-drive grep → use `rg`/`fd`; pip install with no index → add `--find-links`
- **Success criteria verification** (AUTO-02): At task start, parse goal for criteria phrases ("verify that", "make sure", "confirm", "check that", "ensure"). At FINAL ANSWER time, evaluate each criterion against actual state; if any fail, continue rather than terminate.
- **New file**: `core/retry_classifier.py` + `core/stall_monitor.py`.

### Deployment Playbook (DOC-01)

- **Format**: Single markdown file `docs/deployment.md` with sections for:
  - Docker Compose (single-container, volume-mounted workspace)
  - Windows Service via NSSM (`nssm install AgenticOS python main.py`)
  - Kubernetes Deployment manifest (single replica, ConfigMap for config.yaml)
- Written as part of Plan 03-03.

---

## Canonical Refs

- `.planning/REQUIREMENTS.md` — OS-01, OS-02, OS-03, AUTO-01 through AUTO-05, DOC-01 definitions
- `.planning/ROADMAP.md` — Phase 3 goal and success criteria
- `core/orchestrator.py` — existing `repeated_action_count` loop guard (retry classifier runs in parallel, does not replace this)
- `core/task_tracker.py` — extended to support checkpoint writes
- `core/session_memory_sqlite.py` — SQLite backend for checkpoint query/lookup
- `core/dispatcher.py` — `ParallelScheduler.max_workers` is one of the auto-tuned parameters
- `core/context_engine.py` — `compact_history` threshold is auto-tuned by `HardwareProfile`
- `core/model_clients.py` — `FallbackRouter` handles API transient errors; retry classifier handles tool-execution transient errors (different layer)
- `core/platform_api.py` — existing stub to extend or supersede with platform dispatcher

---

## Code Context (Reusable Assets)

| Asset | Location | Relevance |
|-------|----------|-----------|
| `psutil` | `requirements.txt` | CPU/RAM profiling for auto-tuner |
| `pyautogui` | `requirements.txt` | Fallback for cross-platform mouse/keyboard if pywin32/pyobjc unavailable |
| `Pillow` | `requirements.txt` | Screenshot processing after capture |
| `repeated_action_count` | `core/orchestrator.py` | Loop guard — do not modify, classifier runs alongside |
| `FallbackRouter` | `core/model_clients.py` | Handles API retries — retry classifier is for tool execution layer |
| `ParallelScheduler` | `core/dispatcher.py` | `max_workers` is auto-tuned by `HardwareProfile` |
| `compact_history` | `core/context_engine.py` | Compaction threshold auto-tuned by `HardwareProfile` |
| `AgentError` | `core/exceptions.py` | Use for missing-tool and permission errors |
| `@tool` decorator | `core/tool_base.py` | Register all new platform tools via this |

---

## Deferred Ideas

- Multi-node agent orchestration (DIST-01 — already in v2 scope)
- Remote desktop / VNC control (not in scope for v1)
- Full macOS Cocoa widget tree rendering (element screenshot) — defer to Phase 4 if needed
