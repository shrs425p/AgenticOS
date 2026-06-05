---
phase: 2
slug: shell-chaining-obfuscation-interception
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-05
---

# Phase 2 — Validation Strategy

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
- **Before work verification:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | SAFE-01 | — | Block chaining operators outside of active quotes | unit | `venv\Scripts\pytest tests/test_terminal_safety_structural.py` | ✅ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | SAFE-02 | — | Contextual blocking of unquoted variables in command verb / wrapper positions | unit | `venv\Scripts\pytest tests/test_terminal_safety_structural.py` | ✅ W0 | ⬜ pending |
| 02-01-03 | 01 | 1 | SAFE-02 | — | Detect carets, backslashes, and backticks within identifiers | unit | `venv\Scripts\pytest tests/test_terminal_safety_structural.py` | ✅ W0 | ⬜ pending |
| 02-01-04 | 01 | 1 | TEST-01 | — | Verify chaining, variables, and escape validation passes | unit | `venv\Scripts\pytest tests/test_terminal_safety_structural.py` | ✅ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

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
