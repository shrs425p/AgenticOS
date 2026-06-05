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

### Active

- [ ] **SEC-01**: Implement a structural command token parser using `shlex` or structural analysis to replace substring checks.
- [ ] **SEC-02**: Intercept and block command chaining operators (e.g. `;`, `&&`, `||`, `|`, `$()`, `` ` ``).
- [ ] **SEC-03**: Identify and neutralize shell command obfuscation techniques (such as string manipulation, variables, quotes/escapes).
- [ ] **SEC-04**: Write comprehensive test fixtures covering potential shell execution bypass vectors.

### Out of Scope

- **Network-level firewalls** — Out of scope as security is focused entirely on OS/subprocess call interception.
- **Dynamic sandbox virtualization** — Docker or VM sandboxing is out of scope; safety constraints are applied inside the parent process environment.

## Context

- The framework runs Python-based CLI loops (`core/runtime.py`) that call subprocess commands through `tools/terminal/runner.py`.
- Substring-based command validation in `tools/terminal/safety.py` is vulnerable to injection and concatenation bypasses (e.g. `echo hello && sc stop service`).
- Windows execution relies on `shell=True` (due to CMD/PowerShell constraints), which increases shell injection risks.

## Constraints

- **Compatibility**: Must support both Windows (`cmd`/`powershell`) and Unix/macOS (`bash`) shell execution structures.
- **Performance**: Command parsing and validation must complete in <10ms to avoid degrading loop responsiveness.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Use structural command tokenization | Simple substring matching fails to identify chained commands (e.g. `&& net stop`) | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-06-05 after initialization*
