# AgenticOS: Security and Guardrails Manual

Security is not an afterthought in AgenticOS; it is a foundational component of the runtime. This document outlines the multi-layered security architecture designed to prevent unauthorized system access, data exfiltration, and accidental system damage.

---

## The "Zero-Trust" Execution Model

AgenticOS operates on a principle of least privilege. Even when running on a local machine, the agent is restricted by the `PathGuard` and a series of "Hard Guardrails" that cannot be bypassed by the model's reasoning alone.

### Security Layers:
1.  **Zone-Based Path Isolation**: Restricting filesystem access based on directory risk levels.
2.  **Command Validation**: Blocking dangerous shell patterns (e.g., `rm -rf /`, `format C:`).
3.  **Human-In-The-Middle (HITM)**: Forcing manual approval for high-risk operations.
4.  **Performance Safety Gates**: Preventing resource-exhaustion attacks (SSD/RAM thrashing).
5.  **Audit Logging**: Every action is recorded in a non-modifiable SQLite database.

---

## Zone-Based Security (PathGuard)

The `PathGuard` system divides the host machine into four distinct security zones. These zones can be toggled dynamically at runtime without restarting the session by using the `/zone` CLI command (or `/zone 1`, `/zone 2`, `/zone 3`, `/zone 4`).

### 1. The Green Zone (Workspace Isolation)
-   **Definition**: The `workspace/` directory in the project root.
-   **Configuration**: `guard.enabled = True`, `guard.require_hitm = True`, `guard.read_only = False`.
-   **Behavior**: The agent can read, write, and delete files inside the workspace root without any prompts. Write or delete operations outside the workspace are blocked and require human verification (HITM).

### 2. The Yellow Zone (System-Wide Autonomy)
-   **Definition**: The entire filesystem (excluding explicitly blocked paths in the Red Zone).
-   **Configuration**: `guard.enabled = True`, `guard.require_hitm = False`, `guard.read_only = False`.
-   **Behavior**: The agent can write and delete files outside the workspace autonomously without prompting the user. Explicitly blocked system paths are still hard-blocked.

### 3. The Red Zone (PathGuard Disabled)
-   **Definition**: Bypasses all workspace boundaries and path validation checks.
-   **Configuration**: `guard.enabled = False`, `guard.require_hitm = False`, `guard.read_only = False`.
-   **Behavior**: PathGuard is disabled entirely. The agent has unrestricted filesystem access and can read or write anywhere, including previously blocked system directories.

### 4. The Blue Zone (Read-Only / Audit Mode)
-   **Definition**: The entire filesystem is read-only (excluding blocked paths in the Red Zone).
-   **Configuration**: `guard.enabled = True`, `guard.require_hitm = False`, `guard.read_only = True`.
-   **Behavior**: All write and delete operations are blocked globally (both inside and outside the workspace). The agent can only read files, making it ideal for non-destructive auditing and code reviews.


---

## Human-In-The-Middle (HITM)

The HITM system is the ultimate fail-safe. When an agent attempts an operation that crosses a security threshold, the `ToolRegistry` pauses the execution and waits for a physical human response.

### HITM Workflow:
1.  **Intercept**: The `ToolRegistry` identifies a sensitive path (Yellow Zone).
2.  **Pause**: The `Agent` loop is suspended.
3.  **Prompt**: A clear, red-labeled warning appears in the user's terminal:
    ```text
    [STOP] SECURITY GUARDRAIL
    The agent is attempting a WRITE action outside the workspace.
    Target Path: <USER_PROFILE>\Desktop\report.md
    Do you allow this specific action? [y/N]:
    ```
4.  **Resume**: If the user presses `y`, the action is executed once. If `n`, the agent receives a `PermissionError` and must attempt a different (safer) strategy.

---

## Performance Safety Gates (New in v2.0.0)

During stress testing, we identified that agents can accidentally "attack" the host machine by performing massive recursive scans. AgenticOS now includes **Performance Guardrails** to prevent system lockups.

### 1. Root Scan Protection
If an agent attempts to run `find_large_files` or `grep_dir` on the root `<SYSTEM_DRIVE>\` drive using standard Python libraries, the system will **block the execution**.
-   **Rationale**: Python-based file walkers are too slow for millions of files and cause 100% SSD usage.
-   **Enforcement**: The agent is told to use the optimized `fast_disk_audit` tool instead.

### 2. Memory Throttling
-   **Limit**: Any tool output exceeding 4,000 characters is automatically truncated before reaching the model.
-   **Protection**: This prevents the model from being overwhelmed by massive file lists, which could lead to "context poisoning" or memory crashes.

---

## Terminal and Command Validation

The `run_command`, `run_powershell`, and `run_script` tools are the most powerful and dangerous in the registry. To prevent command injection and obfuscation attacks, AgenticOS enforces a zero-trust command validation layer (`SafetyMixin` in [safety.py](../tools/terminal/safety.py)).

### Validation Heuristics:
1.  **AST-like Tokenization**: Splits commands into structural arguments using `shlex` lexical parsing. This ensures nested quotes, escape characters, and spacing cannot bypass the validation rules.
2.  **Chaining Interception**: Scans for command concatenation operators (`&&`, `;`, `||`, `|`, `&`) and blocks execution if chaining is attempted.
3.  **Obfuscation Scans**: Blocks shell escape tick marks, quote variations (e.g., `n""et`), and environment variables constructing execution targets dynamically.
4.  **PowerShell Encoded Command Audit**: Detects parameter prefix matching (e.g., `-e`, `-enc`) and recursively decodes base64-encoded command arguments to validate their plain-text payloads.
5.  **Line-by-Line Script Validation**: Reads shell script files (`.ps1`, `.bat`, `.cmd`, `.sh`, `.bash`) line-by-line, stripping syntax comments and reconstructing line continuation blocks, validating every statement before execution.

### Blocked Patterns:
-   **Disk Formatting**: `format`, `DiskPart`
-   **User Management**: `net user /add`, `passwd`
-   **System Shutdown**: `shutdown`, `restart`, `halt`
-   **Registry Tampering**: `reg delete` (unless `allow_registry_edit` is true)
-   **Mass Deletion**: `rm -rf /`, `del /s /q <SYSTEM_DRIVE>\*`

For detailed validation and script hardening mechanisms, refer to the [Command Validation Guide](command_validation.md).

---

## Audit Logging and Forensic Traceability

Every action taken by the agent is logged in the `audit.jsonl` log file. This file is separate from the chat logs and is intended for forensic review.

### What is logged:
-   **Timestamp**: Precise ISO8601 time.
-   **Tool**: The exact name of the tool called.
-   **Arguments**: The full JSON payload of arguments.
-   **Result**: Success/Failure status.
-   **Path**: Any filesystem path touched.

---

## Secret Redaction Engine (New in v2.0.0)

To prevent sensitive information from leaking into session logs or persistent memory, AgenticOS includes a real-time **Secret Redaction Engine**.

### How it works:
- **Regex Scanning**: Every tool output, observation, and thought block is scanned against a list of high-sensitivity regex patterns (defined in `config/policy.yaml`).
- **In-Memory Masking**: Sensitive strings (API keys, bearer tokens, passwords) are replaced with `[REDACTED]` before being saved to the database or shown in the UI.
- **Privacy First**: This ensures that even if an agent accidentally prints a `.env` file or an API response containing a token, that secret remains private.

---

## Next-Generation Threat Intel & Auditing Plugins (New in v2.1.1)

To achieve maximum protection when interacting with foreign codebases or untrusted remote endpoints, AgenticOS integrates two core security and sandbox audit systems:

### ◆ 1. Cryptographic SSL & WHOIS Threat Scorer (`url_safety_check`)
Before communicating with external domains, the agent can trigger cryptographic and metadata heuristics:
- **Peer Handshake Checking**: Probes the destination server to extract and verify the peer SSL certificate lifecycle, ensuring against expired or self-signed man-in-the-middle attacks.
- **Port 43 WHOIS Registrar Audits**: Establishes raw socket connections to top-level domain registries to parse registration age and check for newly-registered domains (often indicative of high-risk phishing activity).
- **Risk Grading Engine**: Computes a secure compound threat index (0 to 10) mapping certificate trust, domain age, and HTTPS protocols.

### ◆ 2. Dynamic Sandbox Auditing (`os_sandbox_auditor`)
Ensures full visibility into local sandboxing barriers:
- **Runtime Discovery**: Probes and lists compiler paths to ensure the environment is constrained.
- **GUI Process Scanner**: Scans open GUI window handles to check for unauthorized administrative overlays or keyloggers on the desktop, returning process mappings cross-platform.

---

## Security Configuration (`config/policy.yaml`)

Security settings are now centralized in the `config/` directory. The primary file is `policy.yaml`:

```yaml
security:
  # Enable/Disable the entire PathGuard system
  enable_zone_guard: true
  
  # List of paths that are NEVER accessible (Multi-platform paths can be specified)
  blocked_paths: 
    - "%SystemRoot%"
    - "%ProgramFiles%"
    - "/System"
    - "/Library"
    - "/etc"
    - "/sbin"
  
  # Require human approval for actions outside workspace
  require_hitm_outside_workspace: true

redaction:
  # Regex patterns for masking sensitive data
  patterns:
    - "sk-[a-zA-Z0-9]{48}"      # OpenAI Keys
    - "ghp_[a-zA-Z0-9]{36}"     # GitHub Tokens
    - "AIzaSy[a-zA-Z0-9_-]{33}" # Google Keys
```

---

## Best Practices for Developers
1.  **Always use `_resolve()`**: When writing new tools, always resolve paths through the `FileManager` to ensure they are checked against the guardrails.
2.  **Avoid Shell=True**: Use subprocess lists instead of raw strings to prevent shell injection.
3.  **Fail Safely**: If a security check fails, return a clear `PermissionError` so the agent can understand it was a policy block, not a technical bug.
4.  **Use the docs catalog**: Keep security updates synced in [CATALOG.md](CATALOG.md) and [SECURITY.md](../SECURITY.md) so operators can find current guidance quickly.

---

*Last Updated: 2026-05-18*
*Status: Hardened (Multi-Platform)*
