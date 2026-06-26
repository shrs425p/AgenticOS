---
status: complete
phase: 01-kernel-security-and-code-quality-foundation
source:
  - .planning/milestones/v1.0-phases/01-kernel-security-and-code-quality-foundation/01-01-SUMMARY.md
  - .planning/milestones/v1.0-phases/01-kernel-security-and-code-quality-foundation/01-02-SUMMARY.md
  - .planning/milestones/v1.0-phases/01-kernel-security-and-code-quality-foundation/01-03-SUMMARY.md
  - .planning/milestones/v1.0-phases/01-kernel-security-and-code-quality-foundation/01-04-SUMMARY.md
started: "2026-06-26T20:26:00Z"
updated: "2026-06-26T20:26:59Z"
---

## Current Test

[testing complete]

## Tests

### 1. Cold Start Smoke Test
expected: |
  Kill any running server/service. Clear ephemeral state (temp DBs, caches, lock files). Start the application from scratch. Server boots without errors, any seed/migration completes, and a primary query (health check, homepage load, basic CLI call) returns live data.
result: pass

### 2. Obfuscated Character-Encoding Escape Guards
expected: |
  Verify that commands containing Unicode escapes (`\u`, `U+`), Hex escapes (`\x`), and PowerShell character casts (`[char]0xXX`) are successfully detected and blocked by the terminal safety guardrails.
result: pass

### 3. Redirected Script-Write Redirection Targets
expected: |
  Verify that file write redirection targets (`>`, `>>`, `tee`, `Out-File`, `Set-Content`, `Add-Content`) are parsed, and attempts to write scripts outside of the approved workspace roots are intercepted to trigger a HITM confirmation prompt.
result: pass

### 4. Recursive Symlink Depth Validation
expected: |
  Verify that `PathGuard.check_path` resolves path components up to a maximum symlink depth of 5, blocking any circular/infinite symlink loops.
result: pass

### 5. Registry Policy Controls & Custom Exception Framework
expected: |
  Verify that registry access commands are matched against wildcards in dynamic registry policies and restricted/blocked appropriately, throwing a unified `AgentError` with descriptive codes, suggestion arrays, and recovery flags.
result: pass

## Summary

total: 5
passed: 5
issues: 0
pending: 0
skipped: 0

## Gaps

[none yet]
