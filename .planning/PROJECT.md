# AgenticOS Security Hardening

## What This Is

AgenticOS is a secure, high-performance personal AI orchestration framework supporting local and cloud LLMs. This project enhances the zero-trust execution environment of AgenticOS by implementing a robust, AST-like structural command validator to prevent command execution bypasses and obfuscation attacks.

## Core Value

Ensure 100% reliable detection and blocking of unauthorized shell operations without restricting normal, benign terminal tasks.

## Requirements

### Validated

- ✓ **CORE-01**: Execute shell, Python, and PowerShell commands under PathGuard safety rules.
- ✓ **CORE-02**: Enforce zone-based path constraints (Green, Yellow, Red, Blue/Read-Only zones).
- ✓ **CORE-03**: Support Nvidia, Gemini, Groq, and Ollama LLM provider adapters with auto-retry.
- ✓ **CORE-04**: Dynamically discover, validate, and hot-reload modular capability tools and plugins.
- ✓ **CORE-05**: Persist thoughts, actions, and audit logs to local SQLite and structured log files.
- ✓ **SEC-01**: Implement a structural command token parser using `shlex` or structural analysis to replace substring checks. (Validated in Phase 1)
- ✓ **SEC-02**: Intercept and block command chaining operators (e.g. `;`, `&&`, `||`, `|`, `$()`, `` ` ``). (Validated in Phase 2)
- ✓ **SEC-03**: Identify and neutralize shell command obfuscation techniques (such as string manipulation, variables, quotes/escapes). (Validated in Phase 2)
- ✓ **SEC-04**: Write comprehensive test fixtures covering potential shell execution bypass vectors. (Validated in Phase 3)
- ✓ **SEC-05**: Implement recursive base64 decoding and prefix flag matching for PowerShell execution. (Validated in Phase 4)
- ✓ **SEC-06**: Extend script scanning to support Zsh continuation syntax and comments. (Validated in Phase 4)
- ✓ **TEST-01**: Build comprehensive unit and host-OS integration test suites for command safety. (Validated in Phase 4)

### Active

(None)

### Out of Scope

- **Network-level firewalls** — Out of scope as security is focused entirely on OS/subprocess call interception.
- **Dynamic sandbox virtualization** — Docker or VM sandboxing is out of scope; safety constraints are applied inside the parent process environment.

## Context

- The framework runs Python-based CLI loops (`core/runtime.py`) that call subprocess commands through `tools/terminal/runner.py`.
- Substring-based command validation in `tools/terminal/safety.py` is vulnerable to injection and concatenation bypasses (e.g. `echo hello && sc stop service`).
- Windows execution relies on `shell=True` (due to CMD/PowerShell constraints), which increases shell injection risks.
- v1.0 shipped the structural command safety layer, runner integration, script scanning, audit logging, PowerShell encoded command validation, and 35 focused safety tests.

## Current State

**Shipped version:** v1.0 AgenticOS Security Hardening on 2026-06-05.

The security hardening milestone is complete. Requirements `PARS-01`, `PARS-02`, `SAFE-01` through `SAFE-04`, and `TEST-01` are validated and archived in `.planning/milestones/v1.0-REQUIREMENTS.md`.

**Known technical debt:** Ruff may still report cosmetic unused-import warnings in `core/runtime.py` for provider client imports used through dynamic lookup.

## Next Milestone Goals

- Define fresh requirements before starting the next milestone.
- Decide whether v2 admin-control requirements (`ADMIN-01`, `ADMIN-02`) remain the next priority.
- Keep command safety regression tests as a release gate for future runner or terminal changes.

## Constraints

- **Compatibility**: Must support both Windows (`cmd`/`powershell`) and Unix/macOS (`bash`/`zsh`) shell execution structures.
- **Performance**: Command parsing and validation must complete in <10ms to avoid degrading loop responsiveness.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Use structural command tokenization | Simple substring matching fails to identify chained commands (e.g. `&& net stop`) | Implemented in Phase 1 |
| PowerShell Flag Prefix Matching | PowerShell accepts unique prefixes (e.g., `-comm` for `-Command` and `-enc` for `-EncodedCommand`). Strict matching would bypass abbreviations. | Implemented in Phase 4 |
| Recursive Base64 Decoding | Obfuscation via `-EncodedCommand` (UTF-16LE base64) must be recursively validated against all safety rules. | Implemented in Phase 4 |
| Zsh script support | Subprocess scripts can be run via Zsh. Validating comments and continuations prevents bypasses. | Implemented in Phase 4 |
| Hybrid Testing framework | Unit tests cover complex obfuscation combinations in <0.1ms; live integration tests confirm runner tools intercept commands safely. | Implemented in Phase 4 |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition**:
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone**:
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-06-05 after v1.0 milestone completion*
