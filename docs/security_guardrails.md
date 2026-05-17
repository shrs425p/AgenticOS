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

The `PathGuard` system divides the host machine into three distinct security zones.

### 1. The Green Zone (Workspace)
-   **Definition**: The `workspace/` directory in the project root.
-   **Policy**: FULL AUTONOMY.
-   **Behavior**: The agent can read, write, and delete files here without any prompts. This is the "Sandbox" where the agent performs its work.

### 2. The Yellow Zone (Other User Paths)
-   **Definition**: Any path outside the workspace that is not a system path (e.g., `<USER_PROFILE>\Downloads` or `~/Downloads` / `~/Documents`).
-   **Policy**: READ-ONLY AUTONOMY / WRITE-BY-APPROVAL.
-   **Behavior**:
    -   **Read**: The agent can read files (e.g., to analyze a document).
    -   **Write/Delete**: The agent is **BLOCKED**. It must trigger a `HITM_REQUIRED` event, which prompts the user for a `y/N` confirmation in the terminal.

### 3. The Red Zone (System Paths)
-   **Definition**: 
    -   **Windows**: `<SYSTEM_ROOT>\Windows`, `<SYSTEM_DRIVE>\Program Files`, `<SYSTEM_DRIVE>\Program Files (x86)`.
    -   **macOS (Darwin)**: `/System`, `/Library`, `/usr/bin`, `/etc`.
    -   **Linux**: `/etc`, `/sbin`, `/usr/bin`, `/var/run`, `/proc`.
-   **Policy**: STRICTLY FORBIDDEN.
-   **Behavior**: Any attempt to access these paths (even for reading) is blocked at the code level with a `SECURITY ALERT`. The agent cannot bypass this even with "Power Mode" enabled.

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

The `run_command` and `run_powershell` tools are the most powerful and dangerous in the registry. They are protected by a regex-based validator.

### Blocked Patterns:
-   **Disk Formatting**: `format`, `DiskPart`
-   **User Management**: `net user /add`, `passwd`
-   **System Shutdown**: `shutdown`, `restart`, `halt`
-   **Registry Tampering**: `reg delete` (unless `allow_registry_edit` is true)
-   **Mass Deletion**: `rm -rf /`, `del /s /q <SYSTEM_DRIVE>\*`

---

## Audit Logging and Forensic Traceability

Every action taken by the agent is logged in `data/logs/audit.jsonl`. This file is separate from the chat logs and is intended for forensic review.

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

## Next-Generation Threat Intel & Auditing Plugins (New in v2.1.0)

To achieve maximum protection when interacting with foreign codebases or untrusted remote endpoints, AgenticOS integrates two core security and sandbox audit systems:

### 🛡️ 1. Cryptographic SSL & WHOIS Threat Scorer (`url_safety_check`)
Before communicating with external domains, the agent can trigger cryptographic and metadata heuristics:
- **Peer Handshake Checking**: Probes the destination server to extract and verify the peer SSL certificate lifecycle, ensuring against expired or self-signed man-in-the-middle attacks.
- **Port 43 WHOIS Registrar Audits**: Establishes raw socket connections to top-level domain registries to parse registration age and check for newly-registered domains (often indicative of high-risk phishing activity).
- **Risk Grading Engine**: Computes a secure compound threat index (0 to 10) mapping certificate trust, domain age, and HTTPS protocols.

### 💻 2. Dynamic Sandbox Auditing (`os_sandbox_auditor`)
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
    - "C:\\Windows"
    - "C:\\Program Files"
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

---

*Last Updated: 2026-05-18*
*Status: Hardened (Multi-Platform)*
