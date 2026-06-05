# Phase 1: Command Tokenization & Argument Parsing - Context

**Gathered:** 2026-06-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement structural parsing using `shlex` and correctly handle nested quotes and argument splits in a new command validator. This includes exposing the parser as a validator helper class or mixin function.

</domain>

<decisions>
## Implementation Decisions

### Tokenization Strategy
- **D-01**: Use Python's built-in `shlex` module to perform robust structural command line splitting.
- **D-02**: Detect Windows execution context dynamically. When tokenizing on Windows, set `posix=False` inside the `shlex.split` / `shlex.shlex` call to prevent backslashes from being parsed as escape characters (preserving folder paths like `C:\Windows\System32`).

### Obfuscation Normalization
- **D-03**: Extract clean command tokens by stripping wrapping quotes (e.g. `n"e"t` -> `net`, `'sc'` -> `sc`) before validating tokens against safety rules.
- **D-04**: Track internal quote structures. Any command containing highly nested quote pairs within single words (e.g. `s'c'` or `n"e"t`) is flagged as suspicious.

### Safety Registry Integration
- **D-05**: Implement the new validator alongside the existing `SafetyMixin` namespace in `tools/terminal/safety.py`, keeping the class interface clean.

### the agent's Discretion
- Exact warning message strings returned on block events.
- Unit testing setup and mock command lists.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Specifications
- `.planning/PROJECT.md` — Project-wide boundaries, core value, and compatibility constraints.
- `.planning/REQUIREMENTS.md` — Functional requirements for command tokenization and safety block policies.

### Codebase Implementations
- `tools/terminal/safety.py` — Current substring-based validation rules.
- `tools/terminal/runner.py` — Terminal execution mixin.

</canonical_refs>

<specifics>
## Specific Ideas

- Ensure standard commands like `run_command("dir C:\\Users")` split correctly into `['dir', 'C:\\Users']` and aren't matched as substrings of bad commands.
- Safe execution in scripts should allow commands inside single quotes without triggering double-escape errors.

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tools/terminal/safety.py` (`SafetyMixin`): Houses the `rules` dictionary and group rules (e.g., `allow_registry_edit`).

### Established Patterns
- Subprocess execution structure in `tools/terminal/runner.py`: Calls `_blocked_command_reason()` on every terminal execution request.

### Integration Points
- `tools/terminal/safety.py` (`SafetyMixin._blocked_command_reason`): The entry gate where the new structural tokenizer and validator will be hooked.

</code_context>

<deferred>
## Deferred Ideas

- Command concatenation detection (e.g., `&&`, `;`) — Phase 2.
- Environment variables parameter expansion checks — Phase 2.

</deferred>

---

*Phase: 01-command-tokenization-argument-parsing*
*Context gathered: 2026-06-05*
