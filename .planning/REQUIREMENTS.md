# Requirements: AgenticOS

**Defined:** 2026-06-26
**Core Value:** Enable agents to achieve 100% task completion rates on the user's OS runtime with maximum autonomy and complete security, without ever unnecessarily saying "no."

## v1 Requirements

Each of these requirements is active for the v1.0 milestone and maps to roadmap phases.

### Security

- [x] **SEC-01**: The system must detect and block Unicode and hex character-encoding escape sequences (e.g. U+XXXX, \xXX, and PowerShell `$([char]0xXX)` casts) in command tokens.
- [x] **SEC-02**: The system must intercept dynamic code generation commands that attempt to write execution shell scripts or Python scripts directly to disk outside approved paths.
- [x] **SEC-03**: The system must support fine-grained registry policy controls, enabling allowed paths, blocked paths, and paths requiring user-in-the-loop approval.
- [x] **SEC-04**: The system must canonicalize paths and validate symlink path resolution depth (up to 5 levels) to prevent symlink/hardlink traversal exploits.

### Code Quality & Structure

- [x] **QUAL-01**: The system must utilize Pydantic schemas to validate execution action objects, input parameters, and environment config files.
- [x] **QUAL-02**: The main `core/runtime.py` file must be modularized by splitting orchestration, action dispatching, memory management, and error handling into separate sub-modules.
- [x] **QUAL-03**: The system must define a standard `Tool` protocol and register all system and custom tools in a type-safe registry.
- [x] **QUAL-04**: The system must define a unified `AgentError` class containing descriptive error codes and actionable recovery suggestions.

### Documentation

- [x] **DOC-01**: The system must publish a production deployment playbook detailing Docker, Windows Service, K8s, and Serverless configurations.
- [x] **DOC-02**: The system must provide a comprehensive Threat Model mapping potential attack vectors (injection, path traversal, registry edits) to active framework mitigations.
- [x] **DOC-03**: The system must document token estimation heuristics and LLM execution cost projection strategies.

### Performance

- [x] **PERF-01**: The system must implement an adaptive context window engine that dynamically truncates middle messages (collapsing long files/command outputs) to prevent out-of-context crashes.
- [x] **PERF-02**: The system must support streaming and parsing JSON action responses incrementally as they arrive from the LLM, without buffering the entire completion.
- [x] **PERF-03**: The system must offer semantically indexed tool discovery using local vector embeddings (e.g., FAISS) instead of scanning the full tool list.
- [x] **PERF-04**: The system must resolve dependency graphs of requested actions and execute independent tools concurrently.

### OS Control

- [x] **OS-01**: The system must support deep macOS UI control by querying open window lists and clicking menu items via System Events AppleScript and Cocoa accessibility.
- [x] **OS-02**: The system must detect Linux desktop environment sessions (GNOME, KDE, i3, Wayland, X11) and support Wayland-native screenshots (via `grim`/`slurp`).
- [x] **OS-03**: The system must auto-tune its concurrency limits, context sizes, and disk caching based on local system hardware resource footprints (Desktop vs Pi vs IoT).

### Autonomy

- [x] **AUTO-01**: The system must analyze repetition patterns and block retries on permanent logic/permission failures, while allowing retries on transient network or file lock errors.
- [x] **AUTO-02**: The system must parse success criteria from task prompts and verify they are fully met before terminating and returning a final answer.
- [x] **AUTO-03**: The system must estimate execution durations based on task size and raise adaptive stall warnings when a command runs significantly slower than expected.
- [x] **AUTO-04**: The system must support long-term, multi-session tasks by decomposing them into daily/weekly execution phases with persistent state checkpoints.
- [x] **AUTO-05**: The system must identify slow commands and proactively suggest faster alternatives mid-task (e.g., archiving files before copy).

### Extensibility

- [x] **EXT-01**: The system must support asynchronous tool executions implementing async iterators.
- [x] **EXT-02**: The system must support streaming tool output chunks incrementally to the caller.
- [x] **EXT-03**: The system must support downloading and installing community plugins from a remote registry.
- [x] **EXT-04**: The system must resolve tool dependency requirements and check version compatibility.
- [x] **EXT-05**: The system must support piping the output of one tool directly into another tool's input.

### Testing & Resiliency

- [x] **TEST-01**: The system must implement multi-step end-to-end integration workflows (e.g. scrape → summarize → save) in its test suite.
- [x] **TEST-02**: The system must run mutation testing to verify the quality and assertion coverage of its unit test suite.
- [x] **TEST-03**: The system must run performance regression benchmarks to prevent execution speed slowdowns.
- [x] **TEST-04**: The system must include a Chaos Monkey test harness to verify error recovery when simulating LLM timeouts, network failures, or SQLite DB corruption.
- [x] **TEST-05**: The system must include a security regression suite verifying that known command obfuscation and path traversal bypasses are successfully blocked.

### Memory & Context

- [x] **MEM-01**: The system must perform semantic memory lookup using FAISS matching on vector embeddings.
- [x] **MEM-02**: The system must apply mathematical decay functions to memories to prioritize recent context.
- [x] **MEM-03**: The system must group similar past actions into episodic memory clusters.
- [x] **MEM-04**: The system must only retrieve memories that have verified evidence fields.
- [x] **MEM-05**: The system must synchronize memories across distributed agent instances.

### LLM Integration

- [x] **INTEG-01**: The system must route failed calls to fallback models based on failure categories (e.g., fallback to larger context model on context exhaustion).
- [x] **INTEG-02**: The system must utilize cost-aware routing to execute simple tasks on free local models (e.g. Llama) and reserve complex tasks for capable remote APIs.
- [x] **INTEG-03**: The system must format prompts using model-specific system instruction templates.
- [x] **INTEG-04**: The system must guarantee structured outputs by automatically requesting schema-based retries if JSON parsing fails.
- [x] **INTEG-05**: The system must calculate pre-flight token counts and warn users when a task's projected cost exceeds configured thresholds.

## v2 Requirements

Deferred to future releases.

- **DIST-01**: Multi-node agent orchestrations.
- **BIOS-01**: Advanced host BIOS boot parameter configuration.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Multi-tenant hosting | Framework is designed for single-user local operating system execution. |

## Traceability

This table maps v1 requirements to roadmap execution phases. Populated during roadmap generation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| SEC-01 | Phase 1 | Complete |
| SEC-02 | Phase 1 | Complete |
| SEC-03 | Phase 1 | Complete |
| SEC-04 | Phase 1 | Complete |
| QUAL-01 | Phase 1 | Complete |
| QUAL-02 | Phase 1 | Complete |
| QUAL-03 | Phase 1 | Complete |
| QUAL-04 | Phase 1 | Complete |
| DOC-02 | Phase 1 | Complete |
| TEST-05 | Phase 1 | Complete |
| PERF-01 | Phase 2 | Complete |
| PERF-02 | Phase 2 | Complete |
| PERF-03 | Phase 2 | Complete |
| PERF-04 | Phase 2 | Complete |
| INTEG-01 | Phase 2 | Complete |
| INTEG-02 | Phase 2 | Complete |
| INTEG-03 | Phase 2 | Complete |
| INTEG-04 | Phase 2 | Complete |
| INTEG-05 | Phase 2 | Complete |
| DOC-03 | Phase 2 | Complete |
| OS-01 | Phase 3 | Complete |
| OS-02 | Phase 3 | Complete |
| OS-03 | Phase 3 | Complete |
| AUTO-01 | Phase 3 | Complete |
| AUTO-02 | Phase 3 | Complete |
| AUTO-03 | Phase 3 | Complete |
| AUTO-04 | Phase 3 | Complete |
| AUTO-05 | Phase 3 | Complete |
| DOC-01 | Phase 3 | Complete |
| MEM-01 | Phase 4 | Complete |
| MEM-02 | Phase 4 | Complete |
| MEM-03 | Phase 4 | Complete |
| MEM-04 | Phase 4 | Complete |
| MEM-05 | Phase 4 | Complete |
| EXT-01 | Phase 4 | Complete |
| EXT-02 | Phase 4 | Complete |
| EXT-03 | Phase 4 | Complete |
| EXT-04 | Phase 4 | Complete |
| EXT-05 | Phase 4 | Complete |
| TEST-01 | Phase 4 | Complete |
| TEST-02 | Phase 4 | Complete |
| TEST-03 | Phase 4 | Complete |
| TEST-04 | Phase 4 | Complete |

**Coverage:**

- v1 requirements: 43 total
- Mapped to phases: 43
- Unmapped: 0 ✓

---
*Requirements defined: 2026-06-26*
*Last updated: 2026-06-26 after Phase 4 Plan 4*
