# Phase 3: Runner Integration - Context

**Gathered:** 2026-06-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Integrate structural command safety validation with `tools/terminal/runner.py`. Specifically, ensure subprocess calls from terminal tools (such as `run_command`, `run_powershell`, and `run_script`) are validated before running, and return descriptive validation block messages to the caller.

</domain>

<decisions>
## Implementation Decisions

### Script Content Validation Policy
- **D-01:** Implement deep script content scanning. When `run_script` is called on a shell script (`.ps1`, `.bat`, `.cmd`, `.sh`, `.bash`), read the file line-by-line and run each command line through `SafetyMixin._blocked_command_reason`. If any line fails safety validation, block script execution. Non-shell scripts (like `.py` Python scripts) are executed under standard python subprocess constraints.

### Block Error Reporting Interface
- **D-02:** Return formatted error strings. If a command or script is blocked, return `Error: Command blocked by safety rules: [Reason]` to the caller (e.g. orchestrator/agent loop) instead of raising custom exceptions. This aligns with existing runner timeout/not-found behaviors and feeds the block reason back to the agent as a tool observation.

### Audit Logging Integration
- **D-03:** Explicit Security Audit Logging. Record blocked commands and their violation reasons as warning/alert events in the SQLite database audit log via `core/audit_logger.py`.

### the agent's Discretion
- Formatting of error block descriptions.
- Line parsing specifics (e.g. ignoring comment lines and blank lines during script content checks).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Specifications
- `.planning/PROJECT.md` — Project-wide safety boundaries and compatibility constraints.
- `.planning/REQUIREMENTS.md` — Functional security rules (`SAFE-03`, `SAFE-04`).

### Codebase Implementations
- `tools/terminal/runner.py` — The subprocess command executor `RunnerMixin`.
- `tools/terminal/safety.py` — Core safety validator mixin `SafetyMixin`.
- `core/audit_logger.py` — SQLite database audit logger.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `SafetyMixin._blocked_command_reason` in [tools/terminal/safety.py](file:///c:/Users/shrs/AgenticOS/tools/terminal/safety.py): Core validator method.
- `RunnerMixin._run` in [tools/terminal/runner.py](file:///c:/Users/shrs/AgenticOS/tools/terminal/runner.py): The method where all commands eventually route.

### Established Patterns
- `RunnerMixin._run` intercepts commands using `self._blocked_command_reason` and returns error strings on failure.

### Integration Points
- `tools/terminal/runner.py`: Add script line-by-line scanning in `run_script` before delegating to `_run`.
- `core/audit_logger.py`: Connect validation failures to register security alerts/warnings in SQLite database.

</code_context>

<specifics>
## Specific Ideas

- If `exploit.ps1` contains `sc stop spooler`, running `run_script("exploit.ps1")` should be blocked with an informative message.
- A script file run with Python (e.g., `test.py`) will not have its script contents scanned line-by-line as shell commands.

</specifics>

<deferred>
## Deferred Ideas

- Comprehensive verification test suite for safety validator — Phase 4.

</deferred>

---

*Phase: 03-runner-integration*
*Context gathered: 2026-06-05*
