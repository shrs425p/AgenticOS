# AgenticOS: Developer Onboarding & Core Contribution

Welcome to the AgenticOS engineering team! This guide is designed to help you understand the internal architecture, coding standards, and testing procedures required to contribute to the core AgenticOS engine.

---

## [CORE] The Architecture of "Thought"

AgenticOS is built around the **Cortex Engine**. Understanding this loop is the first step to contributing.

1.  **Objective Parser**: Receives the user prompt and breaks it into a high-level goal.
2.  **Strategic Planner**: Drafts a multi-step plan stored in the `agent.plan` attribute.
3.  **Action Dispatcher**: Selects the appropriate tool from the `ToolRegistry` and generates the JSON payload.
4.  **Observer**: Captures tool output, handles errors, and updates the `Memory` system.
5.  **Evaluator**: Compares the observation against the plan to decide if the task is complete.

---

## [SECURE] Coding Standards & Safety

To maintain our "Hardened" status, all core contributions must adhere to these standards:

### 1. Type Safety
Every function in the `core/` and `tools/` directories must have full Python type hinting.
```python
def example_function(path: str, count: int = 10) -> list[str]:
```

### 2. Path Resolution
Never use raw string manipulation for file paths. Always use the internal `_resolve()` helper which ensures the path is checked against the **Zone-Guard** guardrails.

### 3. Subprocess Safety
Avoid `shell=True` when running system commands. Always pass commands as a list of arguments to prevent shell injection.
```python
# GOOD
subprocess.run(["git", "status"], check=True)

# BAD
subprocess.run("git status", shell=True)
```

---

## [TEST] Testing Your Changes

We use a two-tier testing system to ensure stability.

### Tier 1: Unit Tests (Fast)
Located in the `tests/` directory. These test individual functions and tool logic.
```powershell
pytest tests/core/test_registry.py
```

### Tier 2: The Crucible Suite (Comprehensive)
Before any pull request is merged, you must run a selection of the 96 tasks from `task.md` using the evaluation harness.
```powershell
python scripts/run_eval.py --task 5 --task 8 --task 11
```
Verify that:
-   The "Fast-Path" optimizations are triggered.
-   No `429` rate limits cause a crash.
-   The UI remains responsive.

---

## [PLUGIN] Adding New Capabilities

Most developers should contribute by writing **Plugins**.
1.  Create a new file in `tools/plugins/`.
2.  Use the `@tool` decorator.
3.  Provide a robust, 10-line docstring (the model's only source of truth).
4.  Restart the agent or enable `hot_reload: true`.

---

## [DOC] Internal API Documentation

| Module | Responsibility |
| :--- | :--- |
| `core.cortex` | The main reasoning loop and model interaction logic. |
| `core.tool_registry` | Tool discovery, validation, and registration. |
| `core.guardrails` | The PathGuard and CommandValidator implementation. |
| `core.memory` | The SQLite and JSONL persistence layers. |

---

## [END] Onboarding Checklist
- [ ] Read the [Architecture Manual](architecture.md).
- [ ] Set up your local development environment using the [Setup Guide](setup_guide.md).
- [ ] Run the full `pytest` suite.
- [ ] Write a "Hello World" plugin in `tools/plugins/`.
- [ ] Join the internal developer discussion for AgenticOS.

---

*Last Updated: 2026-05-14*
*Status: Engineering Ready*
