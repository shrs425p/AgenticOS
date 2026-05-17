import os
import ast
import datetime
import inspect
import re
from core.tool_registry import ToolRegistry

def check_file(file_path):
    with open(file_path, "r") as f:
        content = f.read()

    try:
        tree = ast.parse(content)
        compile(content, file_path, "exec")
        passes_syntax = True
    except SyntaxError:
        return False, False, False, []

    has_docstring = ast.get_docstring(tree) is not None

    has_callable = False
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            has_callable = True
            break

    # Also extract tools from this file to verify registration later
    ast_tools = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for dec in node.decorator_list:
                if isinstance(dec, ast.Call) and getattr(dec.func, 'id', '') == 'tool':
                    for kw in dec.keywords:
                        if kw.arg == 'name' and isinstance(kw.value, ast.Constant):
                            ast_tools.append(kw.value.value)

    return passes_syntax, has_docstring, has_callable, ast_tools

def get_tool_params(func):
    try:
        sig = inspect.signature(func)
        params = {}
        for name, param in sig.parameters.items():
            if name == "self":
                continue

            if param.annotation is int:
                val = "1"
            elif param.annotation is float:
                val = "1.0"
            elif param.annotation is bool:
                val = "True"
            elif param.annotation is list:
                val = "[]"
            elif param.annotation is dict:
                val = "{}"
            else:
                val = '"mock"'
            params[name] = val
        return params
    except ValueError:
        return {}


def find_test(tool_name):
    tests_dir = "tests"
    for root, dirs, files in os.walk(tests_dir):
        if "auto" in root:
            continue
        for f in files:
            if f.endswith(".py"):
                with open(os.path.join(root, f), "r") as tf:
                    content = tf.read()
                    if f"def test_{tool_name}" in content or f"'{tool_name}'" in content or f'"{tool_name}"' in content or f"{tool_name}(" in content:
                        return True
    return False

def check_ghost_registrations(registry):
    ghost_regs = []
    for name, info in registry.items():
        func = info["fn"]
        try:
            mod_name = func.__module__
            if mod_name and mod_name.startswith("tools."):
                mod_path = mod_name.replace(".", "/") + ".py"
                if not os.path.exists(mod_path):
                    pkg_path = mod_name.replace(".", "/") + "/__init__.py"
                    if not os.path.exists(pkg_path):
                        ghost_regs.append(name)
        except Exception:
            pass
    return ghost_regs

def fix_description_in_file(func, tool_name):
    try:
        source_file = inspect.getsourcefile(func)
        if not source_file or not os.path.exists(source_file):
            return False

        with open(source_file, "r") as f:
            content = f.read()

        # Find @tool(...) and add desc="Auto-generated description"
        pattern = r'(@tool\([^)]*name=[\'"]' + re.escape(tool_name) + r'[\'"][^)]*)(\))'

        # Check if desc is missing
        if re.search(r'@tool\([^)]*name=[\'"]' + re.escape(tool_name) + r'[\'"][^)]*desc=', content):
            # Desc already exists, perhaps we replace it? Or it was "None"?
            # Let's replace desc=None or desc="No description provided"
            content = re.sub(
                r'(@tool\([^)]*name=[\'"]' + re.escape(tool_name) + r'[\'"][^)]*)desc=([\'"]None[\'"]|None|[\'"]No description provided[\'"])([^)]*\))',
                r'\1desc="Auto-generated description"\3',
                content
            )
        else:
            # Inject desc
            content = re.sub(
                pattern,
                r'\1, desc="Auto-generated description"\2',
                content
            )

        with open(source_file, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    except Exception:
        return False

def scan_tool_files(registry_obj):
    tools_dir = "tools"
    all_files = []
    for root, _, files in os.walk(tools_dir):
        for f in files:
            if f.endswith(".py") and f != "__init__.py":
                all_files.append(os.path.join(root, f))

    file_results = {}
    for f in all_files:
        passes_syntax, has_docstring, has_callable, ast_tools = check_file(f)

        # check if properly registered
        unregistered = []
        for t in ast_tools:
            if t not in registry_obj.registry:
                unregistered.append(t)

        file_results[f] = {
            "syntax": passes_syntax,
            "docstring": has_docstring,
            "callable": has_callable,
            "unregistered_tools": unregistered
        }
    return file_results

cfg = {
    "agent": {"workspace": "workspace"},
    "rules": {},
}
registry_obj = ToolRegistry(cfg=cfg)

missing_desc = []
missing_tests = []
seen_names = set()

file_results = scan_tool_files(registry_obj)

duplicate_tools = set()
ast_tools = []
tools_dir = "tools"
for root, _, files in os.walk(tools_dir):
    for f in files:
        if f.endswith(".py"):
            filepath = os.path.join(root, f)
            with open(filepath, 'r') as file:
                try:
                    tree = ast.parse(file.read())
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            for dec in node.decorator_list:
                                if isinstance(dec, ast.Call) and getattr(dec.func, 'id', '') == 'tool':
                                    for kw in dec.keywords:
                                        if kw.arg == 'name' and isinstance(kw.value, ast.Constant):
                                            ast_tools.append(kw.value.value)
                except SyntaxError:
                    pass

for tool_name in set(ast_tools):
    if ast_tools.count(tool_name) > 1:
        duplicate_tools.add(tool_name)

for name, info in registry_obj.registry.items():
    desc = info.get("desc")
    if not desc or desc == "No description provided" or desc == "None":
        missing_desc.append(name)
        registry_obj.registry[name]["desc"] = "Auto-generated description"
        fix_description_in_file(info["fn"], name)

    if not find_test(name):
        missing_tests.append((name, info))

ghost_regs = check_ghost_registrations(registry_obj.registry)

os.makedirs("tests/auto", exist_ok=True)
with open("tests/auto/test_autogenerated.py", "w", encoding="utf-8") as f:
    f.write("import pytest\n")
    f.write("import inspect\n")
    f.write("from core.tool_registry import ToolRegistry\n\n")
    f.write("@pytest.fixture\n")
    f.write("def registry():\n")
    f.write("    cfg = {'agent': {'workspace': 'workspace'}, 'rules': {}}\n")
    f.write("    return ToolRegistry(cfg=cfg)\n\n")

    for name, info in missing_tests:
        params = get_tool_params(info["fn"])
        args_str = ", ".join([f"{k}={v}" for k, v in params.items()])
        f.write(f"def test_{name}(registry):\n")
        f.write(f"    tool_info = registry.registry.get('{name}')\n")
        f.write("    assert tool_info is not None\n")
        f.write("    func = tool_info['fn']\n")
        if info["fn"].__name__ == "<lambda>" and ("open_" in name or "search_" in name):
             f.write("    # Lambda wrapper or preset tool\n")
             f.write("    if 'value' in inspect.signature(func).parameters:\n")
             f.write("        func(value='mock')\n")
             f.write("    else:\n")
             f.write("        func()\n")
        else:
            f.write(f"    func({args_str})\n")
        f.write("\n")

missing_tests_names = [name for name, info in missing_tests]

os.makedirs("workspace/daily_logs", exist_ok=True)
date_str = datetime.datetime.now().strftime("%Y-%m-%d")

health = "GOOD"
if missing_desc or missing_tests_names or ghost_regs or duplicate_tools:
    health = "WARNING"
    if len(missing_desc) > 20 or len(missing_tests_names) > 20 or ghost_regs:
        health = "CRITICAL"

with open(f"workspace/daily_logs/tool_audit_{date_str}.md", "w", encoding="utf-8") as f:
    f.write(f"# Tool Audit {date_str}\n\n")
    f.write(f"- Total tools registered: {len(registry_obj.registry)}\n")
    f.write(f"- Tools with missing descriptions: {missing_desc}\n")
    f.write(f"- Tools with no tests: {missing_tests_names}\n")
    f.write(f"- Ghost registrations found: {ghost_regs}\n")
    f.write(f"- Duplicate tool names: {list(duplicate_tools)}\n")
    f.write(f"- New auto-generated tests added today: {len(missing_tests_names)}\n")
    f.write(f"- Tool registry health: {health}\n\n")
    f.write("## File Checks\n")
    for filepath, res in file_results.items():
        f.write(f"### {filepath}\n")
        f.write(f"- Syntax check passed: {res['syntax']}\n")
        f.write(f"- Has module-level docstring: {res['docstring']}\n")
        f.write(f"- Has at least one callable: {res['callable']}\n")
        f.write(f"- Unregistered tools found: {res['unregistered_tools']}\n\n")
