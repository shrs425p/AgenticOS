# AgenticOS: Autonomous Operations & Autopilot

At its core, AgenticOS is not just a chatbot; it is an **Autonomous Agent**. This document explains the internal decision-making processes, the "Autopilot" mode, and how the system manages complex tasks over long periods.

---

## [LOGIC] The Agent's Internal Monologue

AgenticOS uses a structured reasoning format to ensure consistency and reliability. Depending on the task complexity, the agent uses one of two modes:

### 1. Simple Mode (Action-Observation)
For quick tasks (e.g., "What time is it?"), the agent skips the complex planning and goes straight to:
-   **TASK**: The immediate goal.
-   **STRATEGY**: The tool chosen.
-   **ACTION**: The JSON tool call.

### 2. Complex Mode (Objective-Plan-Step)
For multi-stage tasks (e.g., "Audit my system and write a report"), the agent builds a world-model:
-   **OBJECTIVE**: The final high-level goal.
-   **PLAN**: A numbered list of steps required to reach the objective.
-   **CURRENT_STEP**: The specific sub-task being handled right now.

---

## ✈️ Autopilot vs. Manual Mode

The level of autonomy is controlled by the `autonomy` section in `config.yaml`.

### Autopilot Mode (`autopilot: true`)
-   **High Initiative**: The agent will move through steps of the plan without asking for confirmation.
-   **Silent Self-Healing**: If a tool fails, the agent will autonomously try a different tool or re-read documentation.
-   **Best For**: Background stress tests, long-running audits, and bulk file processing.

### Manual Mode (`autopilot: false`)
-   **High Transparency**: The agent will pause after meaningful steps to explain what it found and ask: *"Shall I proceed to the next step?"*
-   **Best For**: Critical system changes, complex code refactoring, and learning the system.

---

##  Persistent Task Tracking

Unlike simple scripts, AgenticOS maintains its state across restarts. If the system crashes or is interrupted, it can pick up right where it left off.

### State Persistence:
-   **SQLite Database**: Every tool call and its result is stored in `data/memory.sqlite3`.
-   **Workspace Sync**: The agent frequently checks for files it created (e.g., `vulnerability_audit.md`) to verify its own progress.
-   **Resumption Keywords**: If you restart the agent and say "Continue," it will query its own memory to reconstruct its plan.

---

## [SECURE] Expert Mode (`expert_mode: true`)

For power users, `expert_mode` strips away the conversational "fluff." 
-   **Impact**: Responses are shorter, and the agent spends more tokens on pure tool-work rather than explaining itself.
-   **Safety**: Even in expert mode, the **PathGuard** and **HITM** safety checks remain active. You cannot "accidentally" delete system files in expert mode.

---

##  Self-Healing & Fallback Logic

One of the most advanced autonomous features is the **Self-Healing Loop**.

### Error Recovery Scenarios:
1.  **Tool Failure**: If `read_file` fails because the agent guessed the path, it will autonomously call `locate_path` to find the real file.
2.  **Model Hallucination**: If the model outputs a tool name that doesn't exist, the orchestrator returns the full `tools_list` and says: *"That tool doesn't exist. Here is the correct list."*
3.  **JSON Errors**: If the model generates malformed JSON, the agent uses a "Repair Prompt" to fix the syntax and retry the action.

---

## [STATS] Planning Heuristics

AgenticOS uses several heuristics to ensure the plan stays on track:
-   **Loop Detection**: If the agent repeats the exact same tool call 3 times with the same result, it triggers a "Stall Detection" and forces a replan.
-   **Progress Verification**: The agent is instructed to **never** declare a task finished until it has verified the output (e.g., calling `file_exists` on the report it just wrote).

---

## [CONFIG] Configuration Reference

```yaml
autonomy:
  # Toggle the high-level planning block
  active_planning: true
  
  # Hands-off execution
  autopilot: true
  
  # After each action, verify the result worked
  validate_results: true
  
  # DANGEROUS: relaxes some command validation checks
  power_mode: false
```

---

## [END] Summary of Autonomous Best Practices
1.  **Trust the Plan**: Let the agent build its own plan; it is better at understanding its own tool dependencies.
2.  **Monitor the Step**: If the `CURRENT_STEP` doesn't change for 3 iterations, the agent is likely stuck.
3.  **Use Autopilot for Evaluation**: When running the 96-task suite, ensure `autopilot: true` to avoid being prompted for every step.

---

*Last Updated: 2026-05-13*
*Status: Autonomous Operations Enabled*
