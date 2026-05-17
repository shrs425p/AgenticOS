# AgenticOS: Developer Onboarding and Core Contribution

Welcome to the AgenticOS engineering team! This guide is designed to help you understand the internal architecture, coding standards, and testing procedures required to contribute to the core AgenticOS engine.

---

## The Architecture of "Thought"

AgenticOS is built around the **Cortex Engine**. Understanding this loop is the first step to contributing.

1.  **Objective Parser**: Receives the user prompt and breaks it into a high-level goal.
2.  **Strategic Planner**: Drafts a multi-step plan stored in the `agent.plan` attribute.
3.  **Action Dispatcher**: Selects the appropriate tool from the `ToolRegistry` and generates the JSON payload.
4.  **Observer**: Captures tool output, handles errors, and updates the `Memory` system.
5.  **Evaluator**: Compares the observation against the plan to decide if the task is complete.

---

## Coding Standards and Safety

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

## Testing Standards

AgenticOS enforces a high-coverage testing standard using `pytest`. Every new core feature or tool MUST be accompanied by a corresponding test in the `tests/` directory.

### Running Tests
```powershell
# Run the full suite with coverage
pytest tests/ --cov=core --cov=tools --cov-report=term-missing

# Run a specific test file
pytest tests/test_fs_read_write.py
```

### Mocking Guidelines
- **No Live IO**: Use `tmp_path` for filesystem tests.
- **No Live Network**: Use `unittest.mock` to patch `requests.get` or `subprocess.run`.
- **Deterministic**: Tests must be 100% deterministic and pass in a clean CI environment.

---

## Environment Portability Standards

We follow a **Zero-Hardcoding Policy**. The core engine must be 100% environment-agnostic.

### The Rules
1. **No Absolute Paths**: Never use `C:\` or `/home/`. Use `self.cfg.get("workspace")` or `Path.home()`.
2. **No Hardcoded URLs**: All API endpoints and service URLs must reside in `config/endpoints.yaml`.
3. **No Magic Numbers**: Timeouts, retry counts, and heuristic thresholds belong in `config/runtime.yaml`.

### Accessing Config
Inside a tool or core component, use the `self.cfg` helper:
```python
# Fetching an endpoint
api_url = self.cfg.get("endpoints", {}).get("github_api", "https://api.github.com")
```

---

## Adding New Capabilities

Most developers should contribute by writing **Plugins**.
1.  Create a new file in `tools/plugins/`.
2.  Use the `@tool` decorator.
3.  Provide a robust, 10-line docstring (the model's only source of truth).
4.  Restart the agent or enable `hot_reload: true`.

---

## Internal API Documentation

| Module | Responsibility |
| :--- | :--- |
| `core.cortex` | The main reasoning loop and model interaction logic. |
| `core.tool_registry` | Tool discovery, validation, and registration. |
| `core.guardrails` | The PathGuard and CommandValidator implementation. |
| `core.memory` | The SQLite and JSONL persistence layers. |

---

## Onboarding Checklist
- [ ] Read the [Architecture Manual](architecture.md).
- [ ] Set up your local development environment using the [Setup Guide](setup_guide.md).
- [ ] Run the full `pytest` suite.
- [ ] Write a "Hello World" plugin in `tools/plugins/`.
- [ ] Join the internal developer discussion for AgenticOS.

---

*Last Updated: 2026-05-14*
*Status: Engineering Ready*
