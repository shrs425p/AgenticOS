---
phase: 4
slug: safety-verification-suite
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-05
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 |
| **Config file** | pytest.ini |
| **Quick run command** | `pytest tests/test_terminal_safety_structural.py` |
| **Full suite command** | `pytest` |
| **Estimated runtime** | ~1.5 seconds (quick) / ~110 seconds (full) |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_terminal_safety_structural.py`
- **After every plan wave:** Run `pytest tests/test_terminal_safety_structural.py`
- **Before work verification:** Full suite must be green
- **Max feedback latency:** 2 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | TEST-01 | — | Resolve CR-01, WR-01, WR-02 codebase defects | unit | `pytest tests/test_terminal_safety_structural.py` | ✅ | ⬜ pending |
| 04-01-02 | 01 | 1 | TEST-01 | — | Build and verify comprehensive attack matrix test cases | unit/integration | `pytest tests/test_terminal_safety_structural.py` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 5s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-06-05
