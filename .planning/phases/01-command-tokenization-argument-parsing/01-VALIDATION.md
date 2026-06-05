---
phase: 1
slug: command-tokenization-argument-parsing
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-05
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | pytest.ini |
| **Quick run command** | `venv\Scripts\pytest tests/test_terminal_safety_structural.py` |
| **Full suite command** | `venv\Scripts\pytest tests/test_terminal_safety_structural.py` |
| **Estimated runtime** | ~1 second |

---

## Sampling Rate

- **After every task commit:** Run `venv\Scripts\pytest tests/test_terminal_safety_structural.py`
- **After every plan wave:** Run `venv\Scripts\pytest tests/test_terminal_safety_structural.py`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | PARS-01 | — | Structural parsing (shlex) & dynamic OS posix selection | unit | `venv\Scripts\pytest tests/test_terminal_safety_structural.py` | ❌ W0 | ⬜ pending |
| 01-01-02 | 01 | 1 | PARS-02 | — | Recursive check of nested execution wrappers (cmd/pwsh/bash) | unit | `venv\Scripts\pytest tests/test_terminal_safety_structural.py` | ❌ W0 | ⬜ pending |
| 01-01-03 | 01 | 1 | TEST-01 | — | Comprehensive test cases covering normalizations & nesting | unit | `venv\Scripts\pytest tests/test_terminal_safety_structural.py` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_terminal_safety_structural.py` — test file containing test stubs for tokenization, quote handling, and nested execution
- [ ] `tools/terminal/safety.py` — implementation of structural command checking logic hook

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 5s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-06-05
