# Phase 1 Plan 02 Summary: Symlink depth validation

## What was done
- Implemented `resolve_with_symlink_depth` in `core/guardrails.py` to walk path components and resolve symlinks step-by-step up to a maximum depth of 5.
- Replaced Path.resolve() inside `PathGuard.check_path` with the custom depth-limiting resolver.
- Added comprehensive unit tests in `tests/test_guardrails.py`:
  - `test_symlink_depth_real` to test with actual filesystem symlinks (skipped if OS doesn't allow symlink creation).
  - `test_symlink_depth_mocked` to verify depth cutoff and containment checking under mock.

## Verification Results
- Executed `pytest tests/test_guardrails.py` and verified all 20 tests pass.
- Code coverage of `core/guardrails.py` increased to 97%.
