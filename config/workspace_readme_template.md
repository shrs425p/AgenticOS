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

AgenticOS operates under a zero-trust model where the agent has unrestricted access only inside this `workspace/` directory.

- **Green Zone (`workspace/`)**: The agent possesses full read, write, create, and delete permissions.
- **Yellow Zone (System Directories)**: Access is read-only, and any modifications require explicit human validation via terminal prompt.
- **Red Zone (Protected Assets)**: Modifying operating system kernels, security logs, or protected credentials is systematically blocked by the core validation layers.
