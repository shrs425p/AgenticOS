# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.0 — AgenticOS Security Hardening

**Shipped:** 2026-06-05
**Phases:** 4 | **Plans:** 5 | **Sessions:** 1

### What Was Built

- Structural shell-command tokenization using `shlex`, with host-aware Windows handling and recursive wrapper validation.
- Quote-aware chaining and obfuscation interception for shell operators, variable lookups, escaped command names, and nested wrappers.
- Runner integration that blocks unsafe commands before subprocess launch, scans shell scripts line-by-line, and records security validation audit events.
- Verification coverage for PowerShell prefix matching, UTF-16LE base64 payload decoding, Zsh script scanning, and host-OS integration behavior.

### What Worked

- Keeping command parsing centralized in `SafetyMixin` gave the runner integration one clear policy boundary.
- The phase audit cross-checked requirements, verification files, and summaries before milestone closure.
- Focused safety tests made it practical to add bypass cases without broad, slow end-to-end checks.

### What Was Inefficient

- ROADMAP plan counts drifted from executed plan summaries in early phases and required archive-time normalization.
- Some generated planning artifacts carried absolute file URL links that needed cleanup for portability.

### Patterns Established

- Recursive validation of nested shell wrappers before subprocess execution.
- Normalized block response format: `Error: Command blocked by safety rules: ...`.
- Security validation audit records use `where="security_validation"` for easy filtering.

### Key Lessons

1. Treat shell command strings as structured inputs; substring matching is not a reliable security boundary.
2. Verification artifacts should use repository-relative links from the start to avoid machine-specific documentation churn.
3. Safety work benefits from both mocked unit cases and live host-OS integration checks.

### Cost Observations

- Model mix: not recorded.
- Sessions: 1 milestone close session after phase execution.
- Notable: A compact four-phase milestone was enough to move from parser changes through host-level verification.

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v1.0 | 1 | 4 | Established command safety hardening workflow with audit-before-close. |

### Cumulative Quality

| Milestone | Tests | Coverage | Zero-Dep Additions |
|-----------|-------|----------|-------------------|
| v1.0 | 35 focused safety tests | Safety suite passed | Structural parsing used standard library primitives. |

### Top Lessons (Verified Across Milestones)

1. Security-sensitive command execution needs structural parsing and recursive nested-command validation.
2. Milestone archives should stay portable and concise so planning context remains cheap to load.
