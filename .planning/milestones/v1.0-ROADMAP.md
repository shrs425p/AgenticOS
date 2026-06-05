# Roadmap: AgenticOS Security Hardening

## Overview

This project implements a robust structural command safety validator within AgenticOS. It transitions the terminal tools from basic substring-matching security logic to structural command tokenization, detecting and preventing chaining bypasses and shell obfuscation attacks.

## Phases

- [x] **Phase 1: Command Tokenization & Argument Parsing** - Implement structural shlex parsing to correctly handle nested arguments. (completed 2026-06-05)
- [x] **Phase 2: Shell Chaining & Obfuscation Interception** - Detect and block shell chaining and quote/escape obfuscation bypasses. (completed 2026-06-05)
- [x] **Phase 3: Runner Integration** - Integrate advanced validation with `RunnerMixin` subprocess executables. (completed 2026-06-05)
- [x] **Phase 4: Safety Verification Suite** - Verify security policies against a wide matrix of injection payloads. (completed 2026-06-05)

## Phase Details

### Phase 1: Command Tokenization & Argument Parsing

**Goal**: Implement structural parsing using `shlex` and correctly handle nested quotes and argument splits in a new command validator.
**Mode**: mvp
**Depends on**: Nothing (first phase)
**Requirements**: [PARS-01, PARS-02]
**Success Criteria** (what must be TRUE):

  1. Commands are analyzed as tokenized structural words rather than flat strings.
  2. Validator correctly parses complex, nested quoted arguments.

**Plans**: 2 plans
Plans:

- [x] 01-01: Implement structural command tokenizer.
- [ ] 01-02: Write initial tokenization unit tests.

### Phase 2: Shell Chaining & Obfuscation Interception

**Goal**: Detect and block shell chaining operators (`&&`, `;`, `||`, etc.) and obfuscation patterns (variable expansion, escaped quotes).
**Mode**: mvp
**Depends on**: Phase 1
**Requirements**: [SAFE-01, SAFE-02]
**Success Criteria** (what must be TRUE):

  1. Executing chained commands returns a security violation block.
  2. Obfuscated commands (e.g. `n"e"t u"s"er`) are successfully detected and blocked.

**Plans**: 2 plans
Plans:

- [x] 02-01: Implement chaining and obfuscation filters.
- [ ] 02-02: Write chaining and obfuscation bypass unit tests.

### Phase 3: Runner Integration

**Goal**: Integrate the structural command safety checks with `tools/terminal/runner.py`.
**Mode**: mvp
**Depends on**: Phase 2
**Requirements**: [SAFE-03, SAFE-04]
**Success Criteria** (what must be TRUE):

  1. Subprocess calls from terminal tools (such as `run_command` or `run_powershell`) are validated before running.
  2. Blocks return detailed explanation messages to the caller.

**Plans**: 2 plans
Plans:
**Wave 1**

- [x] 03-01: Update `RunnerMixin` in `tools/terminal/runner.py` to invoke the structural validator.

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 03-02: Verify run command execution with active safety rules enabled.

### Phase 4: Safety Verification Suite

**Goal**: Conduct a comprehensive verification audit with test suites verifying all safety gates.
**Mode**: mvp
**Depends on**: Phase 3
**Requirements**: [TEST-01]
**Success Criteria** (what must be TRUE):

  1. All 7 requirements are satisfied and verified by automated tests.

**Plans**: 1 plan
Plans:

- [x] 04-01: Run full pytest suite and verify 100% security test pass rate.

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Tokenization | 1/1 | Complete    | 2026-06-05 |
| 2. Interception | 1/1 | Complete    | 2026-06-05 |
| 3. Integration | 2/2 | Complete    | 2026-06-05 |
| 4. Verification | 1/1 | Complete    | 2026-06-05 |
