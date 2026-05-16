"""Plugin health check module.

Scans all plugins in tools/plugins/ to ensure they have valid syntax,
a module docstring, and at least one callable.
"""

import ast
import os
from datetime import datetime
from pathlib import Path
from typing import Dict

from core.tool_registry import tool


@tool(
    name="plugin_health_check",
    category="System"
)
def plugin_health_check() -> Dict[str, str]:
    """
    Scans all .py files in tools/plugins/.
    For each: checks valid syntax, has docstring, has at least one callable.
    Returns {plugin_name: "ok" | "missing_description" | "syntax_error" | "no_callable"}
    Writes plugin_health_YYYY-MM-DD.md to workspace/daily_logs/
    """
    plugins_dir = Path("tools/plugins")
    results = {}

    if not plugins_dir.exists() or not plugins_dir.is_dir():
        return results

    for filepath in plugins_dir.rglob("*.py"):
        # Skip __init__.py if any
        if filepath.name == "__init__.py":
            continue

        plugin_name = filepath.name

        try:
            content = filepath.read_text(encoding="utf-8")
        except Exception:
            results[plugin_name] = "syntax_error"
            continue

        try:
            tree = ast.parse(content)
        except SyntaxError:
            results[plugin_name] = "syntax_error"
            continue

        # Check for docstring
        if not ast.get_docstring(tree):
            results[plugin_name] = "missing_description"
            continue

        # Check for at least one callable (function or class)
        has_callable = any(isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) for node in tree.body)
        if not has_callable:
            results[plugin_name] = "no_callable"
            continue

        results[plugin_name] = "ok"

    # Write log file
    today_str = datetime.now().strftime("%Y-%m-%d")
    daily_logs_dir = Path("workspace/daily_logs")
    daily_logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = daily_logs_dir / f"plugin_health_{today_str}.md"

    try:
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(f"# Plugin Health Check - {today_str}\n\n")
            if not results:
                f.write("No plugins found.\n")
            else:
                for name, status in results.items():
                    f.write(f"- **{name}**: {status}\n")
    except Exception as e:
        print(f"Warning: Failed to write plugin health check log: {e}")

    return results
