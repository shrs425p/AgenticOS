# Phase 4: Safety Verification Suite - Context

**Gathered:** 2026-06-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Build a comprehensive safety verification test suite inside `tests/` specifically checking the command validator safety and performance limits against a wide matrix of bypass and obfuscation payloads (functional requirement `TEST-01`). Additionally, resolve the security bypasses and logging issues identified in the Phase 3 code review report ([03-REVIEW.md](file:///c:/Users/shrs/AgenticOS/.planning/phases/03-runner-integration/03-REVIEW.md)).

</domain>

<decisions>
## Implementation Decisions

### Remediation of Code Review Findings
- **D-01:** Resolve all findings from Phase 3:
  1. Patch the **CR-01** PowerShell wrapper parameter parsing bypass by implementing prefix-matching logic for PowerShell execution flags (e.g., matching `-comm` to `-Command`) and decode/validate base64 payload variants under `-EncodedCommand` in `tools/terminal/safety.py`.
  2. Patch the **WR-01** missing Zsh script line validation in `tools/terminal/runner.py` by adding `".zsh": "\\"` to the line continuation characters dictionary.
  3. Patch the **WR-02** variable scope warning in `core/runtime.py` to prevent potential `UnboundLocalError` when tool logging fails.
  4. Fix the info-level style issues where appropriate.

### Verification Test Depth
- **D-02:** Use a hybrid testing approach:
  1. Implement comprehensive unit tests utilizing mocks to ensure safety rules and validator behavior are validated under isolated, fast, and cross-platform conditions.
  2. Implement key live integration tests on actual host OS shells (CMD/PowerShell/Bash) to verify that real shell subprocesses execute blocked inputs and result in the correct block errors.

### Attack Matrix Coverage
- **D-03:** The safety verification payload matrix must cover:
  1. Shell chaining/concatenation operators (`&&`, `;`, `||`, `|`, `$()`, backticks).
  2. Command name and parameter quote/tick/escape obfuscation (e.g., `c"a"t`, `c\a\t`, PowerShell ticks).
  3. PowerShell encoded and abbreviated parameters (`-enc`, `-encodedcommand`, etc.).
  4. Environment variable expansions (e.g., `%SystemRoot%`, `$env:windir`, `$HOME`).
  5. Script-based injection vectors (running shell scripts containing interior blocked commands).

### the agent's Discretion
- The exact structure of test cases and helper fixtures.
- Implementation details of PowerShell parameter prefix-matching and Zsh line continuation verification.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Specifications
- `.planning/PROJECT.md` — Project-wide safety boundaries and compatibility constraints.
- `.planning/REQUIREMENTS.md` — Requirement `TEST-01` traceability.

### Codebase Implementations
- `tools/terminal/safety.py` — Core safety validator mixin `SafetyMixin`.
- `tools/terminal/runner.py` — Subprocess command executor `RunnerMixin`.
- `tests/test_terminal_safety_structural.py` — Existing structural safety validation test suite.
- `core/runtime.py` — Runtime loops and tool call handling.
- `.planning/phases/03-runner-integration/03-REVIEW.md` — Findings (CR-01, WR-01, WR-02) that must be resolved.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `SafetyMixin._blocked_command_reason` in [safety.py](file:///c:/Users/shrs/AgenticOS/tools/terminal/safety.py) for the core validation.
- `test_terminal_safety_structural.py` in [test_terminal_safety_structural.py](file:///c:/Users/shrs/AgenticOS/tests/test_terminal_safety_structural.py) which already contains 25 tests that can serve as patterns for the new verification test suite.

### Established Patterns
- Unit testing with mock subprocess/OS functions.
- Normalized safety rule error format checking.

### Integration Points
- `tests/test_terminal_safety_structural.py`: Extend with comprehensive bypass payloads.
- `tools/terminal/safety.py`: Modify parameters parsing checks for prefix matching and `-EncodedCommand` support.
- `tools/terminal/runner.py`: Add `".zsh"` support.
- `core/runtime.py`: Resolve variable scope for `ok` and `obs_text`.

</code_context>

<specifics>
## Specific Ideas
- Cover base64 decoded validation: e.g. calling `powershell -enc c3QgstopIHNwb29sZXI=` (encoded `st stop spooler` or similar) must be blocked because the decoded interior command is unauthorized.
- Cover abbreviated parameter names: `powershell -c "sc stop spooler"` and `powershell -co "sc stop spooler"` and `powershell -comm "sc stop spooler"` must all be blocked.

</specifics>

<deferred>
## Deferred Ideas
- None — discussion stayed within phase scope.

</deferred>

---

*Phase: 04-safety-verification-suite*
*Context gathered: 2026-06-05*
