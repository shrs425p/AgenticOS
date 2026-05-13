# AgenticOS: Evaluation Harness & Stress Testing

The "Hardened" status of AgenticOS was earned through rigorous automated testing. This document explains how the `scripts/run_eval.py` harness works, how to run your own evaluations, and how to interpret the results of the 96-task "Crucible" suite.

---

## [TEST] Purpose of the Harness

In autonomous agent development, small changes in the prompt or code can have catastrophic ripple effects. The Evaluation Harness serves as a **Regression Testing System** to ensure that:
1.  **Safety Guardrails** remain non-bypassable.
2.  **Performance Optimizations** (like the Fast-Path) are actually being used.
3.  **Model Reasoning** hasn't degraded after a config change.

---

## [LAUNCH] Running an Evaluation

The harness is a standalone script that orchestrates the agent through a series of predefined tasks.

### Basic Command:
```powershell
python scripts/run_eval.py
```

### Advanced Flags:
-   **`--task N`**: Runs only a specific task number (e.g., `--task 8` for the Disk Audit).
-   **`--provider nvidia`**: Overrides the default config to test a different model provider.
-   **`--log_level DEBUG`**: Provides extremely verbose output of the orchestrator's decisions.

---

## [PROVEN] The 96-Task "Crucible" Suite

The `task.md` file in the project root contains the full list of production stress tests. These are divided into several categories:

### 1. System Maintenance (Tasks 1-15)
-   **Objective**: Audit the host OS, check disk health, and monitor process telemetry.
-   **Key Success**: The agent must use native PowerShell for the `C:\` drive scan to pass the performance gate.

### 2. Security & Compliance (Tasks 16-30)
-   **Objective**: Audit firewall rules, check for CVEs in installed apps, and analyze event logs.
-   **Key Success**: The agent must identify "Suspicious" items and correctly report them in Markdown.

### 3. Web Research & OSINT (Tasks 31-50)
-   **Objective**: Perform deep web research, check SSL certs, and summarize technical documentation.
-   **Key Success**: The agent must use the `web_search` and `fetch_url` tools effectively without getting stuck in loops.

---

## [DOC] Interpreting the Logs

During an evaluation, the system generates a high-fidelity mirror of the session in `evaluation_output.txt`.

### What to look for in `evaluation_output.txt`:
-   **`Iteration X/1000`**: Tracks how many turns the agent took to solve the task. (Lower is better).
-   **`ACTION: { "tool": "..." }`**: Verify that the agent is choosing the correct tool for the job.
-   **`⚠ Rate limit hit (429)`**: This confirms that the **Resilience Shield** is working correctly.
-   **`OBSERVATION`**: Check the raw output from the tool to ensure it wasn't truncated too early.

---

## [TOOL] Adding Your Own Test Cases

You can expand the evaluation suite by adding new entries to `task.md`.

### Format for New Tasks:
```markdown
- Task Name: [Summary of the goal]
- Success Criteria: [What the agent must produce, e.g., 'A CSV file in workspace/']
- Constraints: [e.g., 'Do not use Python walkers, use PowerShell']
```

The harness will automatically pick up any new bullet points in the `task.md` file.

---

##  Benchmarking Results

The harness produces a summary at the end of the run:
-   **Success Rate**: Percentage of tasks that reached a `FINAL ANSWER`.
-   **Avg. Iterations**: How efficient the agent was.
-   **Failed Tools**: A list of tools that threw exceptions during the run.

### Target Performance for v2.0:
| Metric | Baseline (v1.0) | Target (Hardened v2.0) |
| :--- | :--- | :--- |
| **Task 8 Speed** | 30+ Minutes | < 3 Minutes |
| **API Crash Rate** | 15% (on 429s) | 0% (Auto-retry enabled) |
| **UI Latency** | High (Typewriter) | Zero (Block printing) |

---

## [CONFIG] Harness Configuration

The harness behavior can be tuned in the `logging:` section of `config.yaml`.
-   **`audit_enabled`**: Must be `true` to generate the session mirror.
-   **`audit_format`**: Set to `both` to get both human-readable text and structured JSONL.

---

## [END] Summary
The Evaluation Harness is your primary tool for **Continuous Integration**. Before making a major commit to the AgenticOS core, always run a sample of the Crucible tasks to ensure no safety or performance regressions were introduced.

---

*Last Updated: 2026-05-14*
*Status: Harness Verified*
