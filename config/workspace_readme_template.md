# AgenticOS Workspace

The `workspace/` directory acts as the canonical execution sandbox and persistent data environment for AgenticOS. By default, the system's security guardrails (`PathGuard`) isolate the agent's write operations to this folder, protecting the parent operating system and maintaining a clean isolation boundary.

---

## Directory & File Mapping

```text
workspace/
├── daily_logs/      # Detailed execution and task trace logs grouped by date
├── memory/          # Low-level SQLite database state and raw memory stores
├── reports/         # Output directory for research digests and codebase metrics
├── screenshots/     # Images captured during browser automation and visual tests
├── tasks/           # Process logs and artifacts generated from high-intensity tasks
├── AGENTS.md        # The agent's identity description, behavior guidelines, and safety rules
├── MEMORY.md        # Consolidated long-term memory logs and success patterns
└── USERINFO.md      # Persisted operator profile details (name, preferences)
```

---

## Key Workspace Assets

### 1. Agent Behavior (`workspace/AGENTS.md`)
Declares the identity, operational initiatives, and behavioral constraints of the agent. It enforces:
- **Initiative**: Taking best-effort proactive paths to solve local system problems before requesting assistance.
- **Safety**: Restricting destructive commands, registry edits, and critical service modifications without explicit human approval.

### 2. Long-Term Memory (`workspace/MEMORY.md`)
Tracks experience, success rates, and consolidated memory blocks over time.
- **Success Patterns**: Learned context (e.g., operator names, preferred report layouts, custom shortcuts) is parsed and stored here.
- **Trace History**: Contains links to past logs and execution durations for continuous optimization.

### 3. User Profile (`workspace/USERINFO.md`)
A key-value YAML profile that allows AgenticOS to adapt its language and output formats based on individual operator preferences.

---

## Security Policies (PathGuard Enforcement)

AgenticOS operates under a zero-trust model where the agent's filesystem permissions are governed by four security zones, switchable at runtime using the `/zone` command:

- **Green Zone (`workspace/` isolation)**: The agent has full read and write permissions inside the workspace. Write operations outside the workspace require human validation.
- **Yellow Zone (System-wide write access)**: PathGuard is active, but outside-workspace modifications are allowed autonomously (no human approval required).
- **Red Zone (Protected Assets)**: PathGuard is disabled entirely. The agent has unrestricted filesystem access, bypassing all rules.
- **Blue Zone (Read-Only / Audit)**: All write and delete operations are blocked system-wide. The agent can only read files.

