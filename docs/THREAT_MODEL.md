# AgenticOS Threat Model & Security Architecture

This document details the security posture of AgenticOS, identifying key threat vectors, trust boundaries, STRIDE classification, and framework mitigation mechanisms.

## Trust Boundaries
1. **Agent Runtime vs. Host Operating System**: The barrier protecting the host file system and OS registry from arbitrary execution.
2. **Command Validation Boundary**: Interception of shell strings before being parsed or processed by subprocess runners.
3. **Zone Guard Boundary**: Checking file paths (Green/Yellow/Red zones) dynamically to block access to system credentials and configurations.

---

## Threat Matrix (STRIDE)

| ID | Threat Class | Threat / Vulnerability Vector | Mitigation Mechanism | Verification Metric / Test |
|---|---|---|---|---|
| **T-01-01** | **Elevation of Privilege** | **Unicode/Hex Obfuscation**: Bypassing command blockers using string escape sequences like `\uXXXX`, `\xXX`, or `[char]0xXX`. | Pre-tokenization and post-tokenization regex sweeps in `SafetyMixin`. | `tests/test_security_regression.py` |
| **T-01-02** | **Elevation of Privilege** | **Redirection Script Writing**: Bypassing file tools by writing scripts (`.py`, `.sh`, `.ps1`) outside workspace via shell redirection (`>`) or piping. | Extraction of redirection targets in `SafetyMixin` and running them through `PathGuard`. | `tests/test_security_regression.py` |
| **T-01-03** | **Tampering** | **Registry Tampering**: Modifying startup hives (Run, RunOnce, Services) to establish persistent backdoors or hijack host services. | Config-driven `RegistryGuard` using key path normalization and fnmatch wildcard filters. | `tests/test_security_regression.py` |
| **T-01-04** | **Information Disclosure** | **Symlink Traversal Loops**: Traversing deeply nested or cyclic symlinks to escape the workspace directory. | Enforcing a maximum resolution limit of 5 resolved symlinks during path canonicalization. | `tests/test_security_regression.py` |

---

## Detailed Vulnerability Mitigations

### 1. Command Obfuscation
* **Mechanism**: Static regex filters for Unicode (`UNICODE_ESCAPE_PAT`), hex (`HEX_ESCAPE_PAT`), and PowerShell cast characters (`PS_CHAR_CAST_PAT`) run on raw shell inputs.
* **Double Check**: Cleansed tokens are validated individually to intercept double-escaped payloads.

### 2. Shell Script Redirection Interception
* **Mechanism**: Regex-based redirection parser extracts filenames after `>` or `>>` operators or inside piped commands (`tee`, `Out-File`).
* **Enforcement**: Path verification prevents write actions outside the Green Zone unless explicit HITM user approval is given.

### 3. Registry Policy Controls
* **Mechanism**: `RegistryGuard` checks HKLM/HKCU subkeys during `reg.exe` and PowerShell cmdlet executions.
* **Actions**: Critical keys default to blocked status, while intermediate keys prompt for human-in-the-loop validation (HITM).

### 4. Symlink Depth Restrictions
* **Mechanism**: Path resolution iterates component-by-component, counting symlink lookups.
* **Enforcement**: Exceeding 5 symlink operations triggers a direct security violation error.
