# Requirements: AgenticOS Security Hardening

**Defined:** 2026-06-05
**Core Value:** Ensure 100% reliable detection and blocking of unauthorized shell operations without restricting normal, benign terminal tasks.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Command Parsing

- [x] **PARS-01**: Tokenize subprocess commands using robust structural parsing (e.g. `shlex`) instead of simplistic string checks.
- [x] **PARS-02**: Correctly parse and validate multi-word arguments and double-nested commands.

### Safety Enforcement

- [x] **SAFE-01**: Intercept and block shell chaining/concatenation operators (`&&`, `;`, `||`, `|`, `$()`, `` ` ``).
- [x] **SAFE-02**: Identify and block shell command obfuscation (escapes, variables, env parameter lookups, nested string quotes).
- [x] **SAFE-03**: Integrate the advanced safety checks seamlessly with `run_command`, `run_powershell`, and `run_script` in `tools/terminal/runner.py`.
- [x] **SAFE-04**: Return informative block messages detailing exactly which safety rules were breached.

### Verification

- [x] **TEST-01**: Build unit tests inside `tests/` specifically checking command validator safety against common bypass payloads.

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Admin Controls

- **ADMIN-01**: Implement user warning bypass prompts inside interactive mode to allow single-command exceptions.
- **ADMIN-02**: Dynamically update regex/substring rule filters from `config.yaml` without editing python source files.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Network proxy traffic filtration | Defer to native system firewalls; scope is confined strictly to subprocess calls. |
| Containerized Docker sandboxing | Outside-container sandboxing is complex and out of scope; safety constraints are applied inside the running python runtime process. |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| PARS-01 | Phase 1 | Complete |
| PARS-02 | Phase 1 | Complete |
| SAFE-01 | Phase 2 | Complete |
| SAFE-02 | Phase 2 | Complete |
| SAFE-03 | Phase 3 | Complete |
| SAFE-04 | Phase 3 | Complete |
| TEST-01 | Phase 4 | Complete |

**Coverage:**

- v1 requirements: 7 total
- Mapped to phases: 7
- Unmapped: 0 ✓

---
*Requirements defined: 2026-06-05*
*Last updated: 2026-06-05 after initial definition*
