---
phase: 3
slug: runner-integration
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-05
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 |
| **Config file** | pytest.ini |
| **Quick run command** | `.\\venv\\Scripts\\pytest tests/test_terminal_safety_structural.py` |
| **Full suite command** | `.\\venv\\Scripts\\pytest` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `.\\venv\\Scripts\\pytest tests/test_terminal_safety_structural.py`
- **After every plan wave:** Run `.\\venv\\Scripts\\pytest`
- **Before work verification:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | SAFE-04 | — | Standardized block errors: "Error: Command blocked..." | unit | `.\\venv\\Scripts\\pytest` | ✅ W0 | ⬜ pending |
| 03-01-02 | 01 | 1 | SAFE-03 | — | Deep-scan shell scripts, blocking execution if any line is blocked | unit | `.\\venv\\Scripts\\pytest` | ✅ W0 | ⬜ pending |
| 03-01-03 | 01 | 1 | SAFE-04 | — | SQLite audit database records blocked safety events | integration | `.\\venv\\Scripts\\pytest` | ✅ W0 | ⬜ pending |
| 03-02-01 | 02 | 2 | TEST-01 | — | Unit/integration tests cover runner/script safety blocks | unit | `.\\venv\\Scripts\\pytest` | ✅ W0 | ⬜ pending |

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
- [x] Feedback latency < 10s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-06-05
