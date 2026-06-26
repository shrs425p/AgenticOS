# Phase 3 Discussion Log

**Date:** 2026-06-26  
**Phase:** 03 — Platform OS Control and Autonomy Framework  
**Facilitator:** Antigravity (GSD discuss-phase)

---

## Areas Discussed

### 1. macOS UI Control

| Question | Options Presented | Decision |
|----------|------------------|----------|
| Mechanism | AppleScript-only / pyobjc+Cocoa / Thin wrapper | Agent discretion → thin wrapper (AppleScript primary, optional pyobjc) |
| Scope | Menu/window only / + element inspection / + click/type | Full UI automation (window list, focus, menus, element inspect, click, type) |
| Accessibility permissions | Raise error / Silent no-op / Auto-prompt user | Auto-prompt user to grant permissions and retry |

---

### 2. Linux Desktop Detection & Screenshots

| Question | Options Presented | Decision |
|----------|------------------|----------|
| Detection strategy | Env-var / Runtime probe / Hybrid | Agent discretion → env-var primary + runtime probe fallback |
| Screenshot tool | grim+slurp/scrot / PyGObject / subprocess with existence check | Agent discretion → grim/slurp (Wayland), scrot (X11), subprocess with shutil.which() |

---

### 3. Hardware Auto-Tuning

| Question | Options Presented | Decision |
|----------|------------------|----------|
| Timing | Startup-only / Dynamic / Startup + dynamic throttle | Agent discretion → startup profile + dynamic throttle (re-check every 60s) |
| Parameters | context window / thread workers / disk cache / compaction threshold | Agent discretion → all four, scaled by RAM tier (low/mid/high) |

---

### 4. Multi-Session Checkpoints

| Question | Options Presented | Decision |
|----------|------------------|----------|
| Storage | JSON file / SQLite / Both | Both — JSON primary (fast writes), SQLite secondary (query) |
| Schema | Flat / Hierarchical / Linear phase list | Agent discretion → linear phase list (goal → phases → steps) |

---

### 5. Retry & Stall Classifier

| Question | Options Presented | Decision |
|----------|------------------|----------|
| Transient vs permanent | Error-pattern / Exit-code / Hybrid | Agent discretion → hybrid (exit code primary, pattern fallback) |
| Stall detection | Fixed / Task-size estimated / Command-type threshold | Agent discretion → command-type thresholds (30s/60s/300s) |
| Relationship to loop guard | Extends / Replaces / Parallel | Parallel — different responsibilities (loop guard = signature; classifier = error routing) |

---

### 6. Additional Areas (agent discretion)

- **AUTO-02 Success criteria**: Parse goal for criteria phrases, verify at FINAL ANSWER time
- **AUTO-05 Faster alternatives**: Per-tool-category stall thresholds + lookup table of faster alternatives
- **Windows UI control**: `pywin32` for window enumerate/focus/click/type (Windows-first platform)
- **DOC-01 Deployment playbook**: `manuals/deployment.md` with Docker Compose, Windows Service (NSSM), K8s

---

## Deferred Ideas

- Remote desktop / VNC control — new capability, own phase
- Full macOS Cocoa widget tree rendering — Phase 4 if needed
- Multi-node agent orchestration — already in v2 scope (DIST-01)
