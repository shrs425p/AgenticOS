# AgenticOS: Command Validation and Script Hardening

This document provides a technical specification of the Abstract Syntax Tree (AST)-like command validation and script hardening systems in AgenticOS. These layers form the zero-trust command execution sandbox, designed to block shell injection, obfuscation attacks, and unauthorized system access.

---

## Architecture Overview

Terminal tool executions (`run_command`, `run_powershell`, and `run_script`) are routed through the `SafetyMixin` validation gatekeeper before launching any system subprocess:

```text
       [Command Call]
             │
             ▼
     [SafetyMixin Parser]
             │
     ┌───────┴────────┐
     ▼                ▼
[Single Command]  [Shell Script]
     │                │
     │                ▼
     │        [Line Continuation]
     │                │
     │                ▼
     │        [Comment Filtering]
     │                │
     │        ┌───────┴───────┐
     │        ▼               ▼
     │     [Line 1]        [Line 2] (etc.)
     │        │               │
     └────────┼───────────────┘
              ▼
      [shlex Tokenizer]
              │
              ▼
    [Chaining Detection] (&&, ;, ||, |, $(), `)
              │
              ▼
    [Obfuscation Scan] (escapes, environment vars)
              │
              ▼
     [PowerShell Audit]
     ├─ Abbreviation matching (-e, -enc)
     └─ Base64 payload decoding & recursion
              │
              ▼
    [Command Verb Check] (net, format, shutdown, etc.)
              │
              ├────────────────────────┐
              ▼ (Allowed)              ▼ (Blocked)
       [Subprocess Run]         [Audit Event Log]
                                       │
                                       ▼
                              [Normalized Error]
```

---

## Core Security Layers

### 1. Structural Tokenization (shlex)
Traditional regex-based validators are vulnerable to token splits and quote manipulation. AgenticOS uses Python's standard `shlex` module to perform lexical tokenization:
*   **Quote Context Preservation**: Safely isolates nested single (`'`) and double (`"`) quotes.
*   **Argument Splitting**: Breaks the command string into structural arguments exactly as the OS shell parses them, preventing arguments from being treated as separate executable commands.
*   **Whitespace Normalization**: Collapses arbitrary space characters to prevent token obfuscation.

### 2. Shell Chaining and Concatenation Interception
Attackers frequently inject chaining operators to execute secondary payloads. The validator scans structural tokens for shell operators:
*   **Operators Scanned**: `;`, `&&`, `||`, `|`, `&`.
*   **Subshell Execution**: Detects and blocks subshell execution tokens like `$()` and backticks (`` ` ``).
*   **Mitigation**: If any chaining token is detected outside of a string literal, the entire command is blocked.

### 3. Shell Obfuscation Detection
To bypass basic string matching, commands can be obfuscated using shell escape sequences:
*   **Quote & Tick Obfuscation**: Intercepts commands containing mid-word quotes (e.g., `n""et` or `w''hoami`) and PowerShell backticks (e.g., `d`e`l`).
*   **Environment Variables**: Detects shell variable expansions (e.g., `%SystemRoot%`, `$env:windir`) and blocks them if they attempt to construct execution targets dynamically.

### 4. PowerShell-Specific Defenses
PowerShell offers highly flexible parameter parsing, which is commonly abused in shell attacks:
*   **Abbreviation Prefix Matching**: Detects short forms of PowerShell execution parameters (e.g., `-e`, `-en`, `-enc`, `-enco`, `-encod` matching `-EncodedCommand`).
*   **Base64 Payload Decoding**: When an encoded command flag is detected, the validator extracts the base64 payload, decodes it into plain text, and recursively runs the decoded string through the full safety validation suite.

### 5. Line-by-Line Script Validation
Before executing script files (`.ps1`, `.bat`, `.cmd`, `.sh`, `.bash`), the runner processes them structurally:
*   **Line Continuations**: Reconstructs multi-line instructions broken across lines using platform-specific continuation markers (`\` for Unix/Zsh, `` ` `` for PowerShell, and `^` for Windows CMD).
*   **Comment & Whitespace Stripping**: Ignores comments (`#` for shell/PowerShell, `::` or `rem` for CMD/batch) and blank lines, feeding only active instruction streams to the validator.
*   **Block Isolation**: If even a single line in a script fails safety validation, the entire script execution is blocked.

---

## Safety Policy Reference

The active command validation policy enforces the following restrictions on command verbs:

| Category | Forbidden Commands / Verbs | Rationale |
| :--- | :--- | :--- |
| **Disk Operations** | `format`, `diskpart` | Prevents unauthorized partition or drive formatting. |
| **Identity & Access** | `net user`, `passwd`, `useradd` | Prevents privilege escalation and user account modifications. |
| **Host Lifecycle** | `shutdown`, `restart`, `halt`, `init 0` | Prevents remote denial of service of the host machine. |
| **Registry Mutations** | `reg delete` | Prevents tampering with critical OS registers (configurable). |
| **Destructive File deletion**| `rm -rf`, `del /s /q` | Blocks recursive mass deletions targeting system folders. |

---

## Audit Trail and Normalized Errors

### Error Formatting
When a validation check blocks a command, AgenticOS returns a normalized error string prefix:
```text
Error: Command blocked by safety rules: [Reason]
```
This enables the calling orchestrator loop to programmatically identify safety blocks and react safely.

### SQLite Audit Logs
All safety block incidents are recorded in the system audit trail:
*   **Target Database Table**: `audit_logs` in the persistent SQLite store.
*   **Metadata Tag**: Recorded with `where="security_validation"`.
*   **Payload captured**: Tracks the full blocked command text, the rule violated, and the exact timestamp.

---

## Technical Specifications

*   **Average Validation Latency**: <1.0ms (strictly constrained under the 10.0ms budget to ensure execution loop responsiveness).
*   **Implementation Modules**:
    *   `SafetyMixin` ([tools/terminal/safety.py](../tools/terminal/safety.py))
    *   `RunnerMixin` ([tools/terminal/runner.py](../tools/terminal/runner.py))
    *   `AuditLogger` ([core/audit_logger.py](../core/audit_logger.py))
*   **Test Modules**:
    *   [test_terminal_safety_structural.py](../tests/test_terminal_safety_structural.py)
    *   [test_terminal_safety_integration.py](../tests/test_terminal_safety_integration.py)
