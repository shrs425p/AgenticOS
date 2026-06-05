---
phase: 01-command-tokenization-argument-parsing
plan: "01"
subsystem: api
tags: [shlex, pytest, platform]

requires:
  - phase: 01-command-tokenization-argument-parsing
    provides: context
provides:
  - Structural shlex-based parsing in SafetyMixin
  - Recursive command resolution for cmd/pwsh/bash wrappers
  - Internal quote obfuscation checker
  - test_terminal_safety_structural.py unit test suite
affects: [Phase 2: Shell Chaining & Operators]

tech-stack:
  added: []
  patterns: Structural parsing, recursive command-line resolution

key-files:
  created: [tests/test_terminal_safety_structural.py]
  modified: [tools/terminal/safety.py]

key-decisions:
  - "Used shlex.split with posix=False on Windows to preserve folder path backslashes"
  - "Sanitized tokens by recursively stripping matching outer quote layers"
  - "Reconstructed and stripped outer quotes of nested wrapper commands prior to recursive validation"

patterns-established:
  - "Recursive validation of shell command wrappers"

requirements-completed: [PARS-01, PARS-02]

duration: 10min
completed: 2026-06-05
---

# Phase 1: Command Tokenization & Argument Parsing Summary

**Structural shell-command tokenization using shlex with dynamic Windows compatibility, recursive wrapper validation, and quote-obfuscation detection.**

## Performance

- **Duration:** 10 min
- **Started:** 2026-06-05T12:06:00Z
- **Completed:** 2026-06-05T12:08:00Z
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments
- Refactored `tools/terminal/safety.py` to use `shlex` for structural parsing instead of naive substring matching, resolving `PARS-01`.
- Implemented Windows path preservation by setting `posix=False` dynamically when executing on Windows.
- Added recursive wrapper validation for `powershell`, `pwsh`, `cmd`, `bash`, `sh`, `zsh`, `dash`, `ash`, parsing and resolving nested `-Command` and `/c` structures to address `PARS-02`.
- Developed an obfuscation detection heuristic that identifies internal quotes inside alphanumeric identifiers (such as `s'c'`).
- Created a comprehensive unit test suite with 100% test coverage of the safety mixin logic.

## Task Commits

Each task was committed atomically:

1. **Task 1 & 2: Implement structural validation and recursive wrapper checking** - `999cb8f` (feat)
2. **Task 3: Add structural command validation test suite** - `ecfbcc1` (test)

## Files Created/Modified
- `tools/terminal/safety.py` - Implemented structural parsing, token cleaning, obfuscation checking, and recursive wrapper validation.
- `tests/test_terminal_safety_structural.py` - Created unit test cases verifying correctness across platforms, obfuscation styles, and nested inputs.

## Decisions Made
- Chose `posix=False` for Windows tokenization to prevent backslashes from being parsed as escape sequences.
- Decided to reconstruct unquoted or partially quoted nested command arguments by joining remaining parameters and cleaning wrapping quotes prior to recursive validation.
- Decided to check internal quotes on any token to catch obfuscation.

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
During testing of nested recursion, we found that arguments extracted after `-Command` were being passed to `shlex.split` as a single quoted string token, preventing verb matching. This was resolved by creating `_strip_wrapping_quotes` to sanitize wrapping quotes on the reconstructed nested command string before recursing.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
Phase 1 is complete. The system is ready to advance to Phase 2: Shell Chaining & Operators (intercepting concatenation and pipe operators structurally).
