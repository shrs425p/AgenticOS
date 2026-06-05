# Phase 2: Shell Chaining & Obfuscation Interception - Context

**Gathered:** 2026-06-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement structural detection and blocking for shell chaining operators (`&&`, `;`, `||`, `|`, `$()`, `` ` ``) and command obfuscation techniques (variable expansions, carets, backslashes, and backtick escapes inside identifiers).

</domain>

<decisions>
## Implementation Decisions

### Shell Chaining Operator Interception
- **D-01**: Implement a quote-aware character scanner in `SafetyMixin._blocked_command_reason` to check the raw command string before tokenization. It will flag chaining characters (`&`, `;`, `|`, `` ` ``, and `$(`) if they appear outside of active single or double quotes, preventing evasion via non-spaced operators (e.g. `echo hello;sc stop`) while allowing safe quoted usage (e.g. `echo "hello & welcome"`).

### Variable Expansion Protection
- **D-02**: Enforce contextual variable lookup blocks. Detect environment variables and parameter expansions (`%VAR%`, `$VAR`, `$env:VAR`, `${VAR}`) only if they appear in the command verb position (first token of command/nested command) or inside execution wrapper parameters, allowing benign read-only operations like `echo $PATH` or `echo %USERNAME%`.

### Caret, Backslash, and Backtick Escape Protection
- **D-03**: Extend the `_detect_obfuscation` helper to identify caret `^` (CMD), backslash `\` (Bash), and backtick `` ` `` (PowerShell) escapes inside tokens. Block execution if removing these characters from a token reveals a simple word/identifier (e.g., `n^e^t` -> `net`, `s\c` -> `sc`, `n`e`t` -> `net`).

### Integration Point
- **D-04**: Keep all validation logic contained within the `SafetyMixin` class in `tools/terminal/safety.py`.

### the agent's Discretion
- Specific warning messages on blocking.
- Unit testing setup and mock command lists.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Specifications
- `.planning/PROJECT.md` — Project-wide safety boundaries and compatibility constraints.
- `.planning/REQUIREMENTS.md` — Functional security rules (`SAFE-01`, `SAFE-02`).

### Codebase Implementations
- `tools/terminal/safety.py` — Location of the `SafetyMixin` class.
- `tests/test_terminal_safety_structural.py` — Structural command validation tests.

</canonical_refs>

<specifics>
## Specific Ideas

- Ensure `echo "hello && sc stop"` is allowed.
- Ensure `echo %USERNAME%` is allowed.
- Ensure `%COMSPEC% /c sc stop` is blocked.
- Ensure `n^e^t stop` is blocked.

</specifics>

<deferred>
## Deferred Ideas

- Runner integration and live subprocess interception in `runner.py` — Phase 3.

</deferred>

---

*Phase: 02-shell-chaining-obfuscation-interception*
*Context gathered: 2026-06-05*
