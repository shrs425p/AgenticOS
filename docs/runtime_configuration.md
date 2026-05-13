# AgenticOS: Runtime Configuration Guide (config.yaml)

The `config.yaml` file is the central nervous system of AgenticOS. It controls everything from AI model selection and security guardrails to UI behavior and performance heuristics. This document provides an exhaustive breakdown of every configuration key.

---

## [TOOL] Section 1: Model Providers

### `ollama:`
Configures the local inference engine.
-   **`base_url`**: Usually `http://localhost:11434`.
-   **`default_model`**: The model name (e.g., `qwen2.5-coder:7b`).
-   **`num_ctx`**: The context window size. Increase this for larger coding tasks (up to 32,768).
-   **`temperature`**: Creativity vs. Logic (0.0 to 1.0).

### `cloud:`
Configures external providers (Nvidia, Google, Groq, OpenAI).
-   **`nvidia:`**: Requires `NVIDIA_API_KEY` in `.env`.
-   **`gemini:`**: Requires `GOOGLE_API_KEY` in `.env`.
-   **`max_tokens`**: The generation limit per response.

---

## [SYNC] Section 2: Agent Behavior

### `agent:`
-   **`provider`**: `ollama` or `nvidia`.
-   **`auto_confirm`**: When `true`, the agent skips asking for permission on standard actions.
-   **`self_healing`**: Enables the agent to recover from tool errors or model hallucination loops.
-   **`hot_reload`**: If `true`, you can edit `config.yaml` or plugins without restarting the agent.
-   **`think_before_act`**: Forces the agent to output a "Thoughts" block before calling a tool.

### `autonomy:`
-   **`autopilot`**: Hands-off mode. Minimal questions.
-   **`expert_mode`**: Reduces verbosity and confirmation prompts.
-   **`validate_results`**: After a file operation, the agent performs a check (e.g., `file_exists`) to ensure success.

---

## [SECURE] Section 3: Security & Rules

### `rules:`
These are the hard capability switches.
-   **`allow_file_delete`**: Enables `delete_file` and `delete_dir`.
-   **`allow_shell_exec`**: Enables `run_command` and `run_powershell`.
-   **`allow_system_changes`**: Allows creating scheduled tasks or editing system settings.
-   **`allow_registry_edit`**: Enables Windows Registry modifications.

### `security:`
-   **`enable_zone_guard`**: Activates the PathGuard (Workspace vs. System).
-   **`blocked_paths`**: A list of paths the agent is NEVER allowed to touch (e.g., `C:\Windows`).
-   **`require_hitm_outside_workspace`**: If `true`, writing to any path outside `workspace/` triggers a manual `y/N` prompt.

---

## [STATS] Section 4: Heuristics & Performance

### `heuristics:`
Removes "magic numbers" from the codebase.
-   **`iteration_warning_threshold`**: Warns the user if a single task takes more than N iterations.
-   **`max_dots_in_response`**: Detects "Typing Loops" and breaks them.
-   **`cov_model`**: Dedicated model for Chain-of-Verification (Mental Simulation).

### `performance:`
-   **`max_observation_chars`**: Caps tool output length to prevent context bloat (default: 4,000).
-   **`parallel_execution`**: Allows the orchestrator to run multiple non-conflicting tools (Experimental).

---

## [LOGIC] Section 5: Memory & Persistence

### `memory:`
-   **`backend`**: `json` (simple) or `sqlite` (advanced).
-   **`sqlite_db_path`**: Path to the database file (e.g., `data/memory.sqlite3`).
-   **`summarise_after`**: Number of messages before the agent compresses its history.
-   **`record_artifacts`**: If `true`, the agent logs every file it creates for later auditing.

---

##  Section 6: Logging & Auditing

### `logging:`
-   **`level`**: `DEBUG`, `INFO`, `WARNING`, `ERROR`.
-   **`console_output`**: Toggle real-time terminal printing.
-   **`audit_dir`**: Folder where structured JSONL audit logs are saved.

---

##  Example `config.yaml` (Secure & Verified)

```yaml
agent:
  provider: nvidia
  auto_confirm: true
  hot_reload: true
  self_healing: true

security:
  enable_zone_guard: true
  blocked_paths: ["C:\\Windows", "C:\\Program Files"]
  require_hitm_outside_workspace: true
  hard_guardrails: true

memory:
  backend: sqlite
  record_tool_events: true
  record_artifacts: true

performance:
  max_observation_chars: 12000
  background_tasks: true
```

---

##  How to Apply Changes

1.  **Edit**: Open `config.yaml` in your editor.
2.  **Save**: As soon as you save, the "Hot-Reload" system will detect the change.
3.  **Verify**: Look for `INFO: Config hot-reloaded` in the agent's terminal output.

---

*Last Updated: 2026-05-13*
*Status: Complete Reference*
