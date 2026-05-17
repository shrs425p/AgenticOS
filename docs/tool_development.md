# AgenticOS: Tool & Plugin Development Guide

AgenticOS is designed to be infinitely extensible. Its power comes from its ability to integrate new capabilities through a modular plugin system. This guide explains how to develop, register, and optimize tools for the AgenticOS ecosystem.

---

## [TOOL] The Anatomy of a Tool

In AgenticOS, a tool is a Python function that is:
1.  **Decorated** with the `@tool` decorator.
2.  **Type-hinted** for automatic argument parsing.
3.  **Documented** with a docstring that the LLM uses to understand "When" and "How" to use it.

### Basic Example:
```python
from core.tool_registry import tool

@tool(
    name="get_weather",
    desc="Fetches the current weather for a specific city.",
    category="Web"
)
def get_weather(city: str, units: str = "metric"):
    """
    Connects to a weather API and returns the temperature and conditions.
    Units can be 'metric' or 'imperial'.
    """
    # Implementation logic here...
    return f"The weather in {city} is 22°C and Sunny."
```

---

## [PLUGIN] Developing Plugins

Plugins are dynamic tools loaded from the `tools/plugins/` directory at runtime. This allows you to add new capabilities without modifying the core codebase.

### Step 1: Create the Plugin File
Create a new `.py` file in `c:\AgenticOs\tools\plugins\`. 

### Step 2: Write the Tool Logic
You can import any standard library or installed pip package.

### Step 3: Hot-Reloading
AgenticOS supports **Hot-Reloading**. If `agent.hot_reload` is set to `true` in `config.yaml`, the agent will automatically detect and load your new plugin as soon as you save the file!

---

## [FAST] Performance Optimization (Native vs. Python)

One of the most important lessons from our intensive stress tests is the **Performance Philosophy**:

> **"If it's heavy, use Native. If it's complex, use Python."**

### When to use Python:
-   Data transformation (JSON/CSV processing).
-   API integrations.
-   Logical reasoning and decision making.
-   Small-scale file edits.

### When to use Native (PowerShell/Bash):
-   System-wide file searches.
-   Disk audits.
-   Network topology scans.
-   Process management.

### Pro-Tip: The "Fast-Path" Pattern
When writing a tool that might touch the whole drive, use `subprocess` to call PowerShell. It is 100x faster than `pathlib.rglob`.

---

## [BASE] The Tool Registry Interface

Your tools can interact with the core `FileManager`, `Terminal`, and `Web` classes through the `ToolRegistry`.

### Useful Internal Helpers:
-   `self.cfg`: Access the [Layered Configuration System](runtime_configuration.md).
-   `self._resolve(path)`: Ensures paths are safe and rebased into the workspace.
-   `self._size_human(bytes)`: Formats file sizes for readability.
-   `self.term.run_command(cmd)`: Runs a command through the validated terminal executor.

### Environment Portability
Never hardcode URLs or absolute paths. Use `self.cfg`:
```python
# Fetches an endpoint from config/endpoints.yaml
api_url = self.cfg.get("endpoints", {}).get("github_api")
```

---

## [TEST] Tool Design Best Practices

To ensure your tools are "Agent-Friendly," follow these rules:

### 1. Robust Docstrings
The model *only* sees your docstring. Be explicit about:
-   **Required arguments**.
-   **Expected output format**.
-   **Edge cases** (e.g., "Returns an empty list if no matches found").

### 2. Error Handling
Never let a tool crash the agent loop. Wrap your logic in a `try-except` block and return a helpful string.
```python
try:
    # Logic
except Exception as e:
    return f"Error: Failed to fetch data because {e}"
```

### 3. Truncation Awareness
The model has a context limit. If your tool generates a 5MB JSON file, do **not** return the whole thing. Return a summary or the first 100 lines.

### 4. Verification
If your tool modifies the system (e.g., `create_user`), it should return a confirmation message like `"Successfully created user 'John'. Verified with net user command."`

---

## [FILE] Category Reference

Standardize your tools using these categories to help the LLM organize its thoughts:
-   **Files**: File I/O and metadata.
-   **Terminal**: OS-level commands and scripts.
-   **Web**: Searching, scraping, and APIs.
-   **Browser**: Playwright/Automation tasks.
-   **Media**: Audio and wallpaper controls.
-   **Evolution**: Meta-tools for code modification.

---

## [TOOL] Example: Creating a "Disk Audit" Plugin

Here is a high-performance example of a performance-optimized plugin using the "Native-First" philosophy:

```python
import subprocess
from core.tool_registry import tool

@tool(
    name="quick_disk_audit",
    desc="Uses PowerShell to find the largest files on a drive instantly.",
    category="Files"
)
def quick_disk_audit(self, path: str = None):
    """
    Native implementation for disk analysis. Bypasses Python's slow file crawler.
    """
    # Use config-driven default if no path provided
    target = path or self.cfg.get("runtime", {}).get("default_audit_root", "C:\\")
    
    cmd = f"powershell -Command \"Get-ChildItem -Path '{target}' -File -Recurse | Sort-Object Length -Descending | Select-Object -First 10\""
    try:
        res = subprocess.check_output(cmd, shell=True, text=True)
        return res
    except Exception as e:
        return f"PowerShell failed: {e}"
```

---

## [END] Deployment
Once your plugin is in `tools/plugins/`, run:
```powershell
python main.py
```
Type `/tools` in the console to verify that your new capability is recognized by the system.

---

*Last Updated: 2026-05-13*
*Status: Developer Ready*
