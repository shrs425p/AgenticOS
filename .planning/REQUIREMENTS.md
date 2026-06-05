# Requirements: AgenticOS Security Hardening

**Defined:** 2026-06-05
**Core Value:** Ensure 100% reliable detection and blocking of unauthorized shell operations without restricting normal, benign terminal tasks.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Command Parsing

- [ ] **PARS-01**: Tokenize subprocess commands using robust structural parsing (e.g. `shlex`) instead of simplistic string checks.
- [ ] **PARS-02**: Correctly parse and validate multi-word arguments and double-nested commands.

### Safety Enforcement

- [ ] **SAFE-01**: Intercept and block shell chaining/concatenation operators (`&&`, `;`, `||`, `|`, `$()`, `` ` ``).
- [ ] **SAFE-02**: Identify and block shell command obfuscation (escapes, variables, env parameter lookups, nested string quotes).
- [ ] **SAFE-03**: Integrate the advanced safety checks seamlessly with `run_command`, `run_powershell`, and `run_script` in `tools/terminal/runner.py`.
- [ ] **SAFE-04**: Return informative block messages detailing exactly which safety rules were breached.

### Verification

- [ ] **TEST-01**: Build unit tests inside `tests/` specifically checking command validator safety against common bypass payloads.

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
| PARS-01 | Phase 1 | Pending |
| PARS-02 | Phase 1 | Pending |
| SAFE-01 | Phase 2 | Pending |
| SAFE-02 | Phase 2 | Pending |
| SAFE-03 | Phase 3 | Pending |
| SAFE-04 | Phase 3 | Pending |
| TEST-01 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 7 total
- Mapped to phases: 7
- Unmapped: 0 ✓

---
*Requirements defined: 2026-06-05*
*Last updated: 2026-06-05 after initial definition*
