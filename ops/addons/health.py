"""Plugin health check module.

Scans all plugins in ops/addons/ to ensure they have valid syntax,
a module docstring, and at least one callable.
"""

import ast
from datetime import datetime
from pathlib import Path
from typing import Dict

from kernel.registry import tool
from kernel.settings import DEFAULT_WORKSPACE


@tool(
    name="pluginhealthcheck",
    category="System"
)
def pluginhealthcheck() -> Dict[str, str]:
    """
    Scans all .py files in ops/addons/.
    For each: checks valid syntax, has docstring, has at least one callable.
    Returns {plugin_name: "ok" | "missing_description" | "syntax_error" | "no_callable"}
    Writes plugin_health_YYYY-MM-DD.md to workspace/daily_logs/
    """
    plugins_dir = Path("ops/addons")
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
    daily_logs_dir = Path(DEFAULT_WORKSPACE) / "daily_logs"
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
