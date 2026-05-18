"""Plugin health check module.

Scans all plugins in tools/plugins/ to ensure they have valid syntax,
a module docstring, a @tool decorator, type annotations, and at least
one callable.  Also performs a runtime smoke-test import.

Generates a live ``workspace/plugin_status.html`` dashboard.
"""

import ast
import importlib.util
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from core.tool_registry import tool

# Status constants (exported for use in tests)
STATUS_OK = "ok"
STATUS_SYNTAX_ERROR = "syntax_error"
STATUS_MISSING_DESCRIPTION = "missing_description"
STATUS_NO_CALLABLE = "no_callable"
STATUS_MISSING_TOOL_DECORATOR = "missing_tool_decorator"
STATUS_MISSING_TYPE_ANNOTATIONS = "missing_type_annotations"
STATUS_IMPORT_ERROR = "import_error"


def _check_tool_decorator(tree: ast.Module) -> bool:
    """Return True if at least one function in the module uses @tool."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for decorator in node.decorator_list:
                # Accept @tool or @tool(...)
                if isinstance(decorator, ast.Name) and decorator.id == "tool":
                    return True
                if isinstance(decorator, ast.Call):
                    func = decorator.func
                    if isinstance(func, ast.Name) and func.id == "tool":
                        return True
                    if isinstance(func, ast.Attribute) and func.attr == "tool":
                        return True
    return False


def _check_type_annotations(tree: ast.Module) -> bool:
    """Return True if at least one function has type annotations on its args or return."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.returns is not None:
                return True
            for arg in node.args.args:
                if arg.annotation is not None:
                    return True
    return False


def _smoke_test_import(filepath: Path) -> str:
    """Try to import the module.  Returns '' on success, error string on failure."""
    spec = importlib.util.spec_from_file_location(filepath.stem, filepath)
    if spec is None:
        return "cannot create module spec"
    module = importlib.util.module_from_spec(spec)
    try:
        sys.modules[filepath.stem] = module
        spec.loader.exec_module(module)  # type: ignore[union-attr]
        return ""
    except Exception as exc:
        return str(exc)
    finally:
        sys.modules.pop(filepath.stem, None)


def _build_html_dashboard(results: Dict[str, Dict[str, Any]], today_str: str) -> str:
    """Build a self-contained HTML plugin status dashboard."""

    def _esc(s: str) -> str:
        return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    status_colors = {
        STATUS_OK: "#4caf50",
        STATUS_SYNTAX_ERROR: "#f44336",
        STATUS_MISSING_DESCRIPTION: "#ff9800",
        STATUS_NO_CALLABLE: "#ff9800",
        STATUS_MISSING_TOOL_DECORATOR: "#ff9800",
        STATUS_MISSING_TYPE_ANNOTATIONS: "#ffeb3b",
        STATUS_IMPORT_ERROR: "#f44336",
    }

    rows = ""
    for name, info in sorted(results.items()):
        status = info.get("status", "?")
        color = status_colors.get(status, "#888")
        detail = _esc(info.get("detail", ""))
        rows += (
            f'<tr><td>{_esc(name)}</td>'
            f'<td style="color:{color};font-weight:bold">{_esc(status)}</td>'
            f'<td style="font-size:0.85em;color:#aaa">{detail}</td></tr>\n'
        )

    total = len(results)
    ok_count = sum(1 for v in results.values() if v.get("status") == STATUS_OK)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>AgenticOs Plugin Health — {today_str}</title>
<style>
  body{{background:#1a1a1a;color:#e0e0e0;font-family:monospace;margin:20px}}
  h1{{color:#00bcd4}} table{{border-collapse:collapse;width:100%}}
  th{{background:#263238;padding:8px;text-align:left;color:#80cbc4}}
  td{{padding:6px 8px;border-bottom:1px solid #333}}
  tr:hover{{background:#2a2a2a}}
  .summary{{color:#888;margin-bottom:16px}}
</style>
</head>
<body>
<h1>Plugin Health Dashboard</h1>
<p class="summary">Generated: {today_str} &nbsp;|&nbsp; {ok_count}/{total} plugins healthy</p>
<table>
<tr><th>Plugin</th><th>Status</th><th>Detail</th></tr>
{rows}
</table>
</body>
</html>"""


@tool(
    name="plugin_health_check",
    desc="Deep-scan all plugins: syntax, docstring, @tool decorator, type annotations, and import smoke test. Generates plugin_status.html.",
    category="system",
    version="2.0.0",
)
def plugin_health_check() -> Dict[str, str]:
    """
    Deep-scan all .py files in tools/plugins/.

    Checks:
    1. Valid Python syntax (AST parse)
    2. Module-level docstring present
    3. At least one callable (function/class)
    4. @tool decorator usage
    5. Type annotations present on at least one function
    6. Runtime import smoke test

    Returns a dict mapping plugin filename → status string.
    Writes plugin_health_YYYY-MM-DD.md and plugin_status.html to workspace/daily_logs/.
    """
    plugins_dir = Path("tools/plugins")
    results: Dict[str, Dict[str, Any]] = {}

    if not plugins_dir.exists() or not plugins_dir.is_dir():
        return {}

    for filepath in sorted(plugins_dir.rglob("*.py")):
        if filepath.name == "__init__.py":
            continue

        plugin_name = filepath.name
        detail = ""

        # 1. Read source
        try:
            content = filepath.read_text(encoding="utf-8")
        except Exception as exc:
            results[plugin_name] = {"status": STATUS_SYNTAX_ERROR, "detail": str(exc)}
            continue

        # 2. Parse AST
        try:
            tree = ast.parse(content)
        except SyntaxError as exc:
            results[plugin_name] = {"status": STATUS_SYNTAX_ERROR, "detail": str(exc)}
            continue

        # 3. Module docstring
        if not ast.get_docstring(tree):
            results[plugin_name] = {"status": STATUS_MISSING_DESCRIPTION, "detail": "no module docstring"}
            continue

        # 4. At least one callable
        has_callable = any(
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            for node in tree.body
        )
        if not has_callable:
            results[plugin_name] = {"status": STATUS_NO_CALLABLE, "detail": "no function or class"}
            continue

        # 5. @tool decorator
        if not _check_tool_decorator(tree):
            results[plugin_name] = {
                "status": STATUS_MISSING_TOOL_DECORATOR,
                "detail": "no @tool decorator found",
            }
            continue

        # 6. Type annotations (advisory — only warn)
        has_annotations = _check_type_annotations(tree)
        if not has_annotations:
            detail = "no type annotations"

        # 7. Runtime smoke test import
        import_err = _smoke_test_import(filepath)
        if import_err:
            results[plugin_name] = {
                "status": STATUS_IMPORT_ERROR,
                "detail": import_err[:200],
            }
            continue

        status = STATUS_MISSING_TYPE_ANNOTATIONS if not has_annotations else STATUS_OK
        results[plugin_name] = {"status": status, "detail": detail}

    # Write markdown log
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
                for name, info in sorted(results.items()):
                    status = info.get("status", "?")
                    detail = info.get("detail", "")
                    line = f"- **{name}**: {status}"
                    if detail:
                        line += f" — {detail}"
                    f.write(line + "\n")
    except Exception as e:
        print(f"Warning: Failed to write plugin health check log: {e}")

    # Write HTML dashboard
    try:
        html_path = daily_logs_dir / "plugin_status.html"
        html_content = _build_html_dashboard(results, today_str)
        html_path.write_text(html_content, encoding="utf-8")
    except Exception as e:
        print(f"Warning: Failed to write plugin_status.html: {e}")

    # Return simple status string per plugin (backward-compatible)
    return {name: info["status"] for name, info in results.items()}
