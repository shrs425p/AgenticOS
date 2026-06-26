# Phase 1 Plan 04 Summary: Registry Policies, Errors & Testing

## What was done
- Configured dynamic registry policy definitions under `policy.registry_policies` in `config/policy.yaml` and `.planning/config.json`.
- Implemented `RegistryGuard` in `tools/terminal/safety.py` to normalize registry paths and match them using `fnmatch` wildcard comparisons against allowed, blocked, and approval required key lists.
- Intercepted registry write commands (`reg add`, `reg delete`, `reg import` and PowerShell cmdlets like `Set-ItemProperty`, `New-ItemProperty`, `Remove-ItemProperty`, `New-Item`, etc.) in `SafetyMixin._blocked_command_reason` to validate paths against `RegistryGuard` policies and delegate warnings to the human-in-the-loop (HITM) prompt handler.
- Implemented unified `AgentError` exception class with descriptive error codes, suggestion arrays, and recovery flags in `core/exceptions.py`.
- Formulated the comprehensive security matrix `docs/THREAT_MODEL.md` documenting core vulnerabilities (Unicode bypasses, redirection script writes, registry tampering, symlink traversal) mapped to mitigation methods.
- Implemented a suite of security regression tests verifying registry policies, escape blocks, script redirects, and custom exception types.

## Verification Results
- Executed and verified:
  - `pytest tests/test_security_regression.py` passes (5/5 tests successful).
  - All existing `SafetyMixin` structural command tests pass cleanly.
