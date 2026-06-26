# Phase 1 Plan 04 Summary: Registry Policies, Errors & Testing

## What was done
- Configured dynamic registry policy definitions under `policy.registry_policies` in `cfg/policy.yaml` and `.planning/cfg.json`.
- Implemented `RegistryGuard` in `ops/terminal/safety.py` to normalize registry paths and match them using `fnmatch` wildcard comparisons against allowed, blocked, and approval required key lists.
- Intercepted registry write commands (`reg add`, `reg delete`, `reg import` and PowerShell cmdlets like `Set-ItemProperty`, `New-ItemProperty`, `Remove-ItemProperty`, `New-Item`, etc.) in `SafetyMixin._blocked_command_reason` to validate paths against `RegistryGuard` policies and delegate warnings to the human-in-the-loop (HITM) prompt handler.
- Implemented unified `AgentError` exception class with descriptive error codes, suggestion arrays, and recovery flags in `kernel/errors.py`.
- Formulated the comprehensive security matrix `manuals/threat.md` documenting kernel vulnerabilities (Unicode bypasses, redirection script writes, registry tampering, symlink traversal) mapped to mitigation methods.
- Implemented a suite of security regression spec verifying registry policies, escape blocks, script redirects, and custom exception types.

## Verification Results
- Executed and verified:
  - `pytest spec/securityregressionspec.py` passes (5/5 spec successful).
  - All existing `SafetyMixin` structural command spec pass cleanly.
