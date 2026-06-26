# Phase 1 Plan 02 Summary: Symlink depth validation

## What was done
- Implemented `resolve_with_symlink_depth` in `kernel/guard.py` to walk path components and resolve symlinks step-by-step up to a maximum depth of 5.
- Replaced Path.resolve() inside `PathGuard.check_path` with the custom depth-limiting resolver.
- Added comprehensive unit spec in `spec/guardrailsspec.py`:
  - `test_symlink_depth_real` to test with actual filesystem symlinks (skipped if OS doesn't allow symlink creation).
  - `test_symlink_depth_mocked` to verify depth cutoff and containment checking under mock.

## Verification Results
- Executed `pytest spec/guardrailsspec.py` and verified all 20 spec pass.
- Code coverage of `kernel/guard.py` increased to 97%.
