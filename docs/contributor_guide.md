# Contributor Guide

Welcome to the AgenticOS project! We appreciate your interest in contributing. This guide provides instructions on how to set up your development environment, create and register new plugins, adhere to our coding standards, and run tests.

## Setting Up the Development Environment

1.  **Clone the Repository**
    First, clone the AgenticOS repository to your local machine:
    ```bash
    git clone https://github.com/shrs425p/AgenticOS.git
    cd AgenticOS
    ```

2.  **Environment Setup Script**
    AgenticOS provides an automated setup script that initializes the virtual environment, installs all required dependencies (including Playwright and its browsers), and configures the environment.

    *   **Windows (PowerShell):**
        ```powershell
        powershell -ExecutionPolicy Bypass -File .\setup.ps1
        ```
    *   **macOS/Linux:**
        ```bash
        ./setup.sh
        ```

3.  **Install Development Dependencies**
    If you are planning to contribute, ensure you activate your virtual environment and then install the development dependencies manually if the setup script does not do it:
    ```bash
    # Windows
    .\\venv\\Scripts\\activate
    # macOS/Linux
    source venv/bin/activate

    pip install -r requirements.txt
    pip install -r requirements-dev.txt
    ```

4.  **Configure API Keys**
    Copy the `.env.example` file to `.env` and fill in your API keys (e.g., `NVIDIA_API_KEY`, `GOOGLE_API_KEY`).

## Writing and Registering a New Plugin

AgenticOS boasts a robust ToolRegistry that dynamically loads tools and plugins. Here's how to create and register a new one.

1.  **Create the Plugin File**
    Navigate to the `tools/plugins/` directory and create a new Python file for your plugin, for example, `my_plugin.py`.

2.  **Define the Tool**
    Use the `@tool` decorator to register your function. It is crucial to use the `desc` and `category` arguments in the decorator. Do not use the `description` argument as it will raise a `TypeError`.

    ```python
    from core.tool_registry import tool

    @tool(name="my_custom_tool", desc="A description of what the tool does.", category="Custom")
    def my_custom_tool(arg1: str, arg2: int = 5) -> str:
        """
        Executes a custom action.

        Args:
            arg1 (str): The first argument.
            arg2 (int): The second argument. Default is 5.

        Returns:
            str: The result of the action.
        """
        # Tool implementation
        result = f"Executed with {arg1} and {arg2}"
        return result
    ```

    *Note: When creating tools that require web interactions, use the existing `WebTools` class from `tools.web` instead of making raw HTTP calls to maintain registry consistency.*

## Coding Standards

To ensure a high-quality codebase, please adhere to the following standards:

### 1. No Emojis in Source Code
Do not use emojis in `.py` files to prevent encoding and formatting issues on Windows terminals. Instead, use standard terminal UI symbols and typography characters (e.g., box drawing characters, ✓, ✗, ⚠).

### 2. File Paths
Avoid using hardcoded absolute directories (like `C:\AgenticOs`) in code, documentation, and templates. Use dynamic path resolution placeholders like `<REPO_ROOT>` or rely on the workspace relative paths managed by the system. The `workspace/` directory is meant for task artifacts.

### 3. Type Hints
All functions, especially core engine components and tools, must have full Python type hinting.

```python
def process_data(data: dict, timeout: int = 30) -> list[str]:
    # Implementation
    return ["result"]
```

### 4. Docstrings
Provide robust docstrings for all tools and functions. For tools, the docstring is heavily relied upon by the model to understand how to use the tool. Include clear descriptions, arguments, and return types.

### 5. Logging
Daily system diagnostics, health checks, and dashboard outputs should be written to the `workspace/daily_logs/` directory.

### 6. Linting
The project uses `ruff` for linting. Ensure your code passes linting checks before submitting.
```bash
ruff check .
```

## Running Tests

AgenticOS relies on a comprehensive `pytest` suite to ensure stability.

1.  **Test Execution Command**
    Always run tests using the following command to ensure the correct Python environment and local modules are resolved correctly:
    ```bash
    python -m pytest tests/
    ```

2.  **Generating Coverage Reports**
    To generate JSON test coverage reports, run:
    ```bash
    PYTHONPATH=. python -m pytest --cov --cov-report=json tests/
    ```

3.  **Writing Tests**
    *   **Coverage:** When writing new tests, explicitly target the happy path, at least one error path, and at least one edge case.
    *   **Mocking:** When generating automated tests for tools, underlying functions with side effects must be mocked out to prevent accidental execution of actual tool commands during testing.
    *   **Bug Reporting:** If a bug is discovered while writing tests, do not fix it in production code; report the bug detailing the function, expected vs. actual behavior, and a suggested fix.
    *   **No Artifacts:** Do not commit local test output logs or generated build/test artifacts (e.g., `pytest_output.txt`, `coverage.json`). Avoid creating extraneous log files in the working directory during testing.

Thank you for contributing to AgenticOS!
