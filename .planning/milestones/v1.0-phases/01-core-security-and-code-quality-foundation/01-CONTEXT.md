# Phase 1: Core Security and Code Quality Foundation - Context

**Gathered:** 2026-06-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Solidify the runtime execution environment against Unicode escape sequences, code generation injection, registry tampering, and symlink traversals. Refactor and modularize `kernel/cli.py` into distinct functional layers using Pydantic configuration schemas, a type-safe Tool protocol, and a unified AgentError type.

</domain>

<decisions>
## Implementation Decisions

### Unicode and Escapes Guard
- **D-01:** Block command execution immediately and return a standard `SECURITY POLICY` error when hex, unicode, or PowerShell `$([char]0xXX)` casts are detected. Do not auto-sanitize to avoid double-decoding vulnerabilities.

### Code Generation Intercept
- **D-02:** Detect shell redirection operators (`>`, `>>`, `tee`, etc.) writing scripts (`.py`, `.sh`, `.ps1`, `.bat`) outside approved workspace scratch paths, and enforce HITM (Human-In-The-Loop) validation confirmation before proceeding.

### Fine-grained Registry Controls
- **D-03:** Load allowed, blocked, and approval-required registry key paths dynamically from `.planning/cfg.json` schema. Block critical system startup/run hives by default.

### Symlink Path Traversal
- **D-04:** Enforce a strict traversal limit of 5 resolved symlinks. Exceeding this limit results in an immediate PathGuard violation.

### Modular Core Architecture
- **D-05:** Place common interfaces and protocols in `kernel/base.py`. Register system and custom ops dynamically during runtime initialization to eliminate circular import chains.
- **D-06:** Implement `AgentError` class inheriting from `Exception` capturing standard error codes, message details, recovery feasibility, and suggestions.

### the agent's Discretion
- Exact regex pattern formulations for unicode escape variants.
- Precise directory structure boundaries for modular sub-modules under `kernel/`.
- CLI layout styling for confirmation prompt alerts.

</decisions>

<canonical_refs>
## Canonical References

### Safety and Guardrails
- `manuals/guard.md` — Current pathguard design guidelines.
- `manuals/commands.md` — Existing command sanitization and block rules.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `PathGuard` in `kernel/guard.py`: Checks file path boundaries and zone restrictions.
- `SafetyMixin` in `ops/terminal/safety.py`: Handles regex tokenization and command verb checks.

### Established Patterns
- Blocked actions return normalized error strings which the orchestrator prints or logs.
- Path canonicalization resolves files against workspace root.

### Integration Points
- Command validation hooks directly into terminal runners in `ops/terminal/runner.py`.
- Modularized sub-modules will be loaded and initialized in `kernel/cli.py`.

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---
*Phase: 01-kernel-security-and-code-quality-foundation*
*Context gathered: 2026-06-26*
