---
phase: 1
slug: core-security-and-code-quality-foundation
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-26
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pytest.ini |
| **Quick run command** | `pytest tests/test_safety.py` |
| **Full suite command** | `pytest` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_safety.py`
- **After every plan wave:** Run `pytest`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | SEC-01 | T-01-01 | Block unicode escapes | unit | `pytest tests/test_safety.py -k test_unicode_escapes` | ❌ W0 | ⬜ pending |
| 01-01-02 | 01 | 1 | SEC-02 | T-01-02 | Intercept script writes | unit | `pytest tests/test_safety.py -k test_code_gen_redirect` | ❌ W0 | ⬜ pending |
| 01-02-01 | 02 | 1 | SEC-04 | T-01-03 | Symlink depth validation | unit | `pytest tests/test_safety.py -k test_symlink_depth` | ❌ W0 | ⬜ pending |
| 01-03-01 | 03 | 1 | QUAL-01 | — | Validate config schemas | unit | `pytest tests/test_config.py` | ❌ W0 | ⬜ pending |
| 01-04-01 | 04 | 1 | TEST-05 | T-01-04 | Run security regressions | unit | `pytest tests/test_security_regression.py` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_safety.py` — stubs for SEC-01, SEC-02, and SEC-04
- [ ] `tests/test_config.py` — stubs for QUAL-01
- [ ] `tests/test_security_regression.py` — stubs for TEST-05

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Registry Policy HITM Prompt | SEC-03 | Interactive prompt needs human response | Modify registry key outside allowed path, verify console stops and asks for input |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 10s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
