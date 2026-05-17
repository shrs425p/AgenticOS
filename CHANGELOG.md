## [2.0.0] - 2026-05-14

### New Features
- Fast-Path PowerShell Tooling: Replaced inefficient Python-based recursive crawlers with native PowerShell pipelines.
- Persistent SQLite Memory: Migrated session memory to a structured SQLite database.
- No-Lag UI: Optimized the terminal rendering engine to use block-level output.

### Performance Improvements
- Crucible Stress Test: Successfully completed the 96-task autonomous audit of a live Windows system.
- Disk Hygiene: Scanned 1M+ files on C:\ in < 3 minutes using native PowerShell optimization.
- Resource Efficiency: Maintained stable RAM usage (<150MB) during high-intensity 60-iteration tasks.

### Security Hardening
- Zone-Based PathGuard: Implemented a non-bypassable security layer that restricts the agent to specific filesystem zones (Green, Yellow, Red).
- Security Audit: Successfully identified 12+ suspicious scheduled tasks and non-standard firewall ports.

### Bug Fixes
- API Resilience / Exponential Backoff Shield: Handled over 50+ "429 Rate Limit" errors flawlessly without a single agent crash.

## [2026-05-16]

### New Features
- [eb1fbdd] feat: add daily maintenance plugins and tests (#15) (Shreyas Pawar)
