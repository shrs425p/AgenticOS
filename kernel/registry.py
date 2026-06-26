"""Tool registration and dispatch for the AgenticOs runtime."""

import inspect
import urllib.parse
import time
import ast
import math
import operator
import requests
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable

# Subsystems are imported dynamically in __init__ to avoid circular imports.

from kernel.settings import DEFAULT_WORKSPACE
from kernel.presets import load_url_presets
from kernel.validate import validate_tool
from .guard import PathGuard
from kernel.base import tool
from kernel.events import OSEventBus

import importlib.util
import os
import sys
import logging
import asyncio



class ToolRegistry:
    def __init__(
        self,
        cfg: dict,
        memory_backend: Optional[Any] = None,
        confirm_handler: Optional[Callable] = None,
    ):
        self.cfg = cfg
        # Merge cfg-controlled policy surfaces. Code should expose capability;
        # cfg.yaml decides what is enabled, guarded, or restricted.
        self.rules = {
            **cfg.get("performance", {}),
            **cfg.get("system_control", {}),
            **cfg.get("security", {}),
            **cfg.get("rules", {}),
        }
        self.ops_cfg = cfg.get("ops", {})
        self.disabled_ops = {
            str(name).lower()
            for name in self.ops_cfg.get("disabled_ops", []) or []
        }
        self.disabled_categories = {
            str(name).lower()
            for name in self.ops_cfg.get("disabled_categories", []) or []
        }
        self.essential_ops = {
            str(name).lower()
            for name in self.ops_cfg.get("essential_ops", []) or []
        }
        self._memory = memory_backend

        workspace = self.cfg.get("agent", {}).get("workspace", DEFAULT_WORKSPACE)

        # Dynamic imports to resolve circular import dependencies
        import importlib
        filesystem = importlib.import_module("ops.files")
        terminal = importlib.import_module("ops.shell")
        web = importlib.import_module("ops.web")
        notifications = importlib.import_module("ops.notify")
        screen = importlib.import_module("ops.screen")
        ocr = importlib.import_module("ops.ocr")
        system_ops = importlib.import_module("ops.system")

        self.fm = filesystem.FileManager(rules=self.rules, base_dir=workspace)
        self.term = terminal.TerminalExecutor(
            rules=self.rules,
            custom_keys=cfg.get("custom_keys", {}),
            cfg=self.cfg,
        )
        self.web = web.WebTools(rules=self.rules, base_dir=workspace, cfg=self.cfg)
        self.ui = notifications.NotificationCenter(rules=self.rules, cfg=self.cfg)
        self.screen = screen.ScreenManager(rules=self.rules, base_dir=workspace)
        self.ocr = ocr.OCRManager(rules=self.rules, base_dir=workspace, registry=self, cfg=self.cfg)
        self.sys_mgr = system_ops.SystemManager(rules=self.rules, cfg=self.cfg)
        self.event_bus = OSEventBus(cfg=self.cfg)
        self._notepad: List[str] = []
        self._canvas: str = ""
        self.registry: Dict[str, Dict[str, Any]] = {}
        self._register_all()
        self._load_plugins()  # <--- Load dynamic plugins
        self._workspace_root = Path(workspace).resolve()
        self.guard = PathGuard(cfg, on_confirm=confirm_handler)
        self.term.guard = self.guard
        self.shadow_mode = False

    def _register_all(self):
        """Authoritative tool registration using dynamic inspection and URL presets."""
        # 1. Dynamic registration for kernel subsystems
        for obj, category in [
            (self.fm, "Files"),
            (self.term, "Terminal"),
            (self.web, "Web"),
            (self.ui, "General"),
            (self.screen, "General"),
            (self.ocr, "Media"),
            (self.event_bus, "System"),
            (self, "Core"),
        ]:
            self._register_subsystem(obj, category)
        self._register_subsystem(self.sys_mgr, "System")



        # 2. Dynamic registration for URL presets
        if self.ops_cfg.get("url_presets", True):
            for preset in load_url_presets(self.cfg):
                tool_name = preset.get("tool", "")
                mode = preset.get("mode", "direct")
                url = preset.get("url", "")
                desc = preset.get("desc", "Open preset URL.")
                if not tool_name or not url:
                    continue

                if mode == "direct":
                    def _mk_direct(u):
                        return lambda: self.term.openurl(u)
                    self._reg(tool_name, _mk_direct(url), desc)
                elif mode in ("query", "path"):
                    def _mk_value(u):
                        def _fn(value="", query="", url="", **_):
                            val = value or query or url or ""
                            v = urllib.parse.quote(val.strip())
                            return self.term.openurl(u.format(value=v))
                        return _fn
                    self._reg(tool_name, _mk_value(url), desc)

    def _register_subsystem(self, obj, default_category="General"):
        """Register all methods of an object decorated with @tool."""
        for attr_name in dir(obj):
            attr = getattr(obj, attr_name)
            if callable(attr) and hasattr(attr, "_is_tool"):
                name = getattr(attr, "_tool_name")
                desc = getattr(attr, "_tool_desc")
                category = getattr(attr, "_tool_category", default_category)
                self._reg(name, attr, desc, category=category)



    def _load_plugins(self):
        """Scan ops/addons/ (and subdirectories) for any .py files and register functions with @tool."""
        plugin_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "ops", "addons"
        )
        if not os.path.isdir(plugin_dir):
            return

        for root, _, files in os.walk(plugin_dir):
            for filename in files:
                if filename.endswith(".py") and filename != "__init__.py":
                    file_path = os.path.join(root, filename)
                    # Build a stable module name based on the plugin path to avoid
                    # clobbering top-level module names in sys.modules.
                    rel_path = os.path.relpath(file_path, plugin_dir)
                    mod_path = rel_path[:-3].replace(os.path.sep, ".")
                    full_mod_name = f"ops.addons.{mod_path}"

                    if full_mod_name in sys.modules:
                        self._register_module_ops(sys.modules[full_mod_name])
                        continue

                    try:
                        spec = importlib.util.spec_from_file_location(
                            full_mod_name, file_path
                        )
                        if spec and spec.loader:
                            module = importlib.util.module_from_spec(spec)
                            sys.modules[full_mod_name] = module
                            spec.loader.exec_module(module)
                            # Register any decorated @tool functions found in the module
                            self._register_module_ops(module)
                    except Exception:
                        logging.exception("[PLUGIN ERROR] Failed to load %s", file_path)

    def _register_module_ops(self, module, default_category="Plugins"):
        """Register all decorated @tool callables found in a module."""
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if callable(attr) and hasattr(attr, "_is_tool"):
                name = getattr(attr, "_tool_name")
                desc = getattr(attr, "_tool_desc", "")
                category = getattr(attr, "_tool_category", default_category)
                self._reg(name, attr, desc, category=category)

    def _reg(self, name, fn, desc, category="General"):
        """Register a tool, skipping duplicates silently (first registration wins)."""
        name_l = str(name).lower()
        category_l = str(category or "General").lower()
        if name_l in self.disabled_ops:
            return
        if category_l in self.disabled_categories and name_l not in self.essential_ops:
            return
        if name in self.registry:
            # Silently skip duplicates - first registration (from @tool decorators) takes precedence
            return
        self.registry[name] = {"fn": fn, "desc": desc, "category": category}

    @tool(name="calculate", category="Core")
    def _calculate(self, expression: str) -> str:

        allowed = {
            key: getattr(math, key) for key in dir(math) if not key.startswith("_")
        }
        allowed.update({"abs": abs, "round": round, "min": min, "max": max, "sum": sum})
        operators = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.FloorDiv: operator.floordiv,
            ast.Mod: operator.mod,
            ast.Pow: operator.pow,
            ast.USub: operator.neg,
            ast.UAdd: operator.pos,
        }

        def evaluate(node):
            """evaluate function."""
            if isinstance(node, ast.Expression):
                return evaluate(node.body)
            if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
                return node.value
            if isinstance(node, ast.BinOp) and type(node.op) in operators:
                return operators[type(node.op)](
                    evaluate(node.left), evaluate(node.right)
                )
            if isinstance(node, ast.UnaryOp) and type(node.op) in operators:
                return operators[type(node.op)](evaluate(node.operand))
            if isinstance(node, ast.Name) and node.id in allowed:
                return allowed[node.id]
            if isinstance(node, ast.Call):
                fn = evaluate(node.func)
                if fn not in allowed.values():
                    raise ValueError("Unsupported function")
                return fn(*(evaluate(arg) for arg in node.args))
            raise ValueError("Unsupported expression")

        try:
            return str(evaluate(ast.parse(expression, mode="eval")))
        except Exception as exc:
            return f"Error: {exc}"

    @tool(name="currentdatetime", category="Core")
    def _now(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @tool(name="timestamp", category="Core")
    def _timestamp(self) -> str:
        return str(int(time.time()))



    @tool(name="opscount", category="Core")
    def opscount(self) -> str:
        """Return the authoritative count of currently registered ops."""
        return str(len(self.registry))

    @tool(name="opslist", category="Core")
    def opslist(self) -> str:
        """Return the authoritative list of currently registered ops (one per line)."""
        return "\n".join(sorted(self.registry.keys()))

    @tool(name="memorysearch", category="Core")
    def memorysearch(self, query: str, limit: int = 10) -> str:
        """Search recent conversation memory for a substring (backend-agnostic)."""
        q = (query or "").strip().lower()
        if not q:
            return "Error: query required."
        try:
            msgs = []
            if self._memory and hasattr(self._memory, "get_messages"):
                msgs = self._memory.get_messages()
            hits = []
            for m in msgs or []:
                role = (m.get("role") or "").upper()
                content = m.get("content") or ""
                if q in content.lower():
                    preview = content.replace("\n", " ")
                    if len(preview) > 240:
                        preview = preview[:240] + "..."
                    hits.append(f"{role}: {preview}")
            if not hits:
                return "No matches."
            return "\n".join(hits[-int(limit) :])
        except Exception as e:
            return f"Error: {type(e).__name__}: {e}"

    @tool(name="downloadsmart", category="Core")
    def downloadsmart(self, url: str, dest_path: str) -> str:
        """Download with retries/fallbacks and post-checks.

        Strategy:
        1) requests streaming download (no shell interpolation)
        2) built-in web.downloadfile fallback
        Always validates dest exists and size > 0.
        """
        import os
        from pathlib import Path

        u = (url or "").strip()
        dst = (dest_path or "").strip()
        if not u or not dst:
            return "Error: url and dest_path required."

        parsed = urllib.parse.urlparse(u)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return "Error: only absolute http(s) URLs are supported."

        if os.path.isabs(dst):
            dst_path = Path(dst).resolve()
        else:
            ws = self.cfg.get("agent", {}).get("workspace", DEFAULT_WORKSPACE)
            dst_path = (Path(ws) / dst).resolve()
        try:
            dst_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

        attempts = []

        # 1) requests. Avoid shelling out with user-controlled URL/path values.
        try:
            download_timeout = self.cfg.get("timeouts", {}).get("web_download", 120)
            with requests.get(u, stream=True, timeout=download_timeout) as resp:
                resp.raise_for_status()
                size = 0
                with dst_path.open("wb") as handle:
                    for chunk in resp.iter_content(chunk_size=1024 * 64):
                        if not chunk:
                            continue
                        handle.write(chunk)
                        size += len(chunk)
            attempts.append("requests")
            if dst_path.exists() and dst_path.stat().st_size > 0:
                return (
                    f"Downloaded {size} bytes to {dst_path}"
                    + f"\nVALIDATION: downloaded via requests (size={dst_path.stat().st_size})"
                )
        except Exception:
            pass

        # 2) WebTools fallback.
        try:
            out = self.web.downloadfile(u, str(dst_path))
            attempts.append("web.downloadfile")
            if dst_path.exists() and dst_path.stat().st_size > 0:
                return (
                    out
                    + f"\nVALIDATION: downloaded via web.downloadfile (size={dst_path.stat().st_size})"
                )
            return out + "\nVALIDATION: download failed (file missing/empty)"
        except Exception as e:
            return f"Error: download failed after {attempts}: {type(e).__name__}: {e}"

    def call(self, name: str, args) -> str:
        """call function."""
        if name not in self.registry:
            available = ", ".join(list(self.registry.keys())[:15])
            return f"Unknown tool: '{name}'. Available: {available}..."

        # ── Security Guardrails & Shadow Mode ─────────────────────────────────
        policy = self.cfg.get("policy", {})
        write_ops = set(policy.get("write_ops", [
            "replace_in_dir", "writejson", "writecsv", "runcommand",
            "runpowershell", "runscript", "runpython", "startbackground",
            "hotkey", "presskey", "typetext", "mouseclick", "mousemove"
        ]))

        # Shadow Mode Interception
        if self.shadow_mode and name in write_ops:
            return f"[SHADOW MODE] Dry run: would have executed '{name}' with args: {args}. Result simulated as SUCCESS."

        # ── Universal Path Guardrails ─────────────────────────────────────────
        # Automatically protect any argument that looks like a path
        path_keys = set(policy.get("path_keys", [
            "path", "src", "dst", "dest_path", "filename", "output_path", "directory"
        ]))
        read_only_ops = set(policy.get("read_only_ops", [
            "fileinfo", "readjson", "readcsv", "fileexists", "filehash"
        ]))

        if isinstance(args, dict):
            for key, val in args.items():
                if key.lower() in path_keys:
                    op = "read" if name in read_only_ops else "write"
                    allowed, msg = self.guard.check_path(str(val), operation=op)
                    if not allowed:
                        if msg == "HITM_REQUIRED":
                            if not self.guard.ask_human(str(val), name):
                                return f"SECURITY POLICY: The user has explicitly DENIED the '{name}' action on '{val}'. Do not attempt this action again or try to bypass this restriction."
                        else:
                            return msg
        elif isinstance(args, list) and len(args) > 0:
            # Fallback for positional args (assume first arg might be a path if tool is file-related)
            if any(
                t in name for t in ["file", "dir", "path", "read", "write", "delete"]
            ):
                op = "read" if name in read_only_ops else "write"
                allowed, msg = self.guard.check_path(str(args[0]), operation=op)
                if not allowed:
                    if msg == "HITM_REQUIRED":
                        if not self.guard.ask_human(str(args[0]), name):
                            return f"SECURITY POLICY: The user has explicitly DENIED the '{name}' action on '{args[0]}'. Do not attempt this action again or try to bypass this restriction."
                    else:
                        return msg
        # ──────────────────────────────────────────────────────────────────────

        try:
            fn = self.registry[name]["fn"]
            sig = inspect.signature(fn)
            params = [
                param
                for param in sig.parameters.values()
                if param.kind in (param.POSITIONAL_OR_KEYWORD, param.POSITIONAL_ONLY)
            ]

            def _invoke(func):
                is_async = getattr(func, "_is_async", False) or asyncio.iscoroutinefunction(func)
                if isinstance(args, dict):
                    kwargs = {}
                    for p in params:
                        if p.name in args:
                            kwargs[p.name] = args[p.name]
                    if is_async:
                        async def async_run():
                            res = await func(**kwargs)
                            out = str(res)
                            note = ""
                            if self.cfg.get("autonomy", {}).get("validate_results", True):
                                note = validate_tool(name, args, out, workspace_root=self._workspace_root)
                            return f"{out}\n{note}".strip() if note else out
                        return async_run()
                    else:
                        out = str(func(**kwargs))
                        note = ""
                        if self.cfg.get("autonomy", {}).get("validate_results", True):
                            note = validate_tool(name, args, out, workspace_root=self._workspace_root)
                        return f"{out}\n{note}".strip() if note else out

                clean_args = [arg for arg in (args or []) if (isinstance(arg, str) and arg.strip()) or not isinstance(arg, str)]
                param_count = len(params)
                if len(clean_args) > param_count > 0:
                    joined = "|".join(str(arg) for arg in clean_args[param_count - 1 :])
                    clean_args = clean_args[: param_count - 1] + [joined]

                converted = []
                for arg in clean_args:
                    if not isinstance(arg, str):
                        converted.append(arg)
                        continue
                    stripped = arg.strip()
                    if stripped.lstrip("-").isdigit():
                        converted.append(int(stripped))
                    elif stripped.replace(".", "", 1).lstrip("-").isdigit() and stripped.count(".") == 1:
                        converted.append(float(stripped))
                    else:
                        converted.append(stripped)

                if is_async:
                    async def async_run_pos():
                        res = await func(*converted) if converted else await func()
                        out = str(res)
                        if getattr(self, "sentinel", None):
                            self.sentinel.log_action(name, args, out)
                        note = ""
                        if self.cfg.get("autonomy", {}).get("validate_results", True):
                            note = validate_tool(name, converted, out, workspace_root=self._workspace_root)
                        return f"{out}\n{note}".strip() if note else out
                    return async_run_pos()
                else:
                    out = str(func(*converted)) if converted else str(func())
                    if getattr(self, "sentinel", None):
                        self.sentinel.log_action(name, args, out)
                    note = ""
                    if self.cfg.get("autonomy", {}).get("validate_results", True):
                        note = validate_tool(name, converted, out, workspace_root=self._workspace_root)
                    return f"{out}\n{note}".strip() if note else out

            try:
                return _invoke(fn)
            except (ModuleNotFoundError, ImportError) as exc:
                if name in write_ops:
                    raise
                module_name = getattr(exc, "name", None)
                if not module_name:
                    import re
                    match = re.search(r"No module named '([^']+)'", str(exc))
                    if match:
                        module_name = match.group(1)
                if module_name:
                    logging.info(f"Self-healing: Missing module '{module_name}' detected. Attempting to install...")
                    try:
                        import subprocess
                        subprocess.run([sys.executable, "-m", "pip", "install", module_name], capture_output=True)
                    except Exception:
                        pass

                    importlib.invalidate_caches()
                    mod_name = fn.__module__
                    new_fn = fn
                    if mod_name and mod_name in sys.modules and mod_name.startswith("ops.addons."):
                        try:
                            importlib.reload(sys.modules[mod_name])
                            new_fn = getattr(sys.modules[mod_name], fn.__name__)
                            self.registry[name]["fn"] = new_fn
                        except Exception as e:
                            logging.warning(f"Self-healing: Could not reload module {mod_name}: {e}")
                    return _invoke(new_fn)
                raise
            except FileNotFoundError as exc:
                if name in write_ops and name not in {"writejson", "writecsv"}:
                    raise

                # Exclude purely read operations from creating parent directories
                if name in read_only_ops:
                    raise

                filename = getattr(exc, "filename", None)
                if filename:
                    parent_dir = os.path.dirname(filename)
                    if parent_dir and not os.path.exists(parent_dir):
                        allowed, msg = self.guard.check_path(parent_dir, operation="write")
                        if allowed:
                            logging.info(f"Self-healing: Missing parent directory '{parent_dir}'. Creating...")
                            os.makedirs(parent_dir, exist_ok=True)
                            return _invoke(fn)
                raise
        except TypeError as exc:
            return f"Tool argument error ({name}): {exc}\n  Expected: {self._get_signature(name)}"
        except PermissionError as exc:
            return f"Permission denied ({name}): {exc}"
        except FileNotFoundError as exc:
            return f"File not found ({name}): {exc}"
        except Exception as exc:
            return f"Tool error ({name}): {type(exc).__name__}: {exc}"

    def _get_signature(self, name: str) -> str:
        if name in self.registry:
            try:
                return str(inspect.signature(self.registry[name]["fn"]))
            except Exception:
                pass
        return "unknown"

    def get_symbol(self, name: str) -> str:
        """get_symbol function."""
        name = name.lower()
        symbols = self.cfg.get("ui", {}).get("category_symbols", {
            "files": {"tokens": ["file", "read", "write", "dir", "delete", "path", "move"], "symbol": "[F]"},
            "terminal": {"tokens": ["run", "exec", "cmd", "ps", "terminal", "shell"], "symbol": "[T]"},
            "web": {"tokens": ["web", "search", "get", "post", "url", "scrape"], "symbol": "[W]"},
            "math": {"tokens": ["calc", "math", "sum", "average"], "symbol": "[M]"},
            "notes": {"tokens": ["note", "pad", "list", "clear"], "symbol": "[N]"},
            "canvas": {"tokens": ["canvas"], "symbol": "[C]"},
            "system": {"tokens": ["sys", "cpu", "mem", "process", "service"], "symbol": "[S]"},
            "registry": {"tokens": ["reg", "key", "value"], "symbol": "[R]"},
        })
        
        for cat, data in symbols.items():
            tokens = data.get("tokens", [])
            symbol = data.get("symbol", "[*]")
            if any(token in name for token in tokens):
                return symbol
        return "[*]"

    def tool_descriptions(self) -> str:
        """tool_descriptions function."""
        max_lines = int(self.cfg.get("prompts", {}).get("max_tool_descriptions", 140))
        
        # Group ops by category
        categories = {}
        for name, info in self.registry.items():
            cat = info.get("category", "General")
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(f"  {name}: {info['desc']}")

        # Build description string with headers
        output_lines = []
        total_count = 0
        
        # Prioritize kernel and high-value categories
        priority = ["Core", "Media", "Files", "Terminal", "Web", "Browser", "System"]
        sorted_cats = sorted(categories.keys(), key=lambda x: (priority.index(x) if x in priority else 999, x))
        
        for cat in sorted_cats:
            if total_count >= max_lines:
                break
            output_lines.append(f"\n[{cat.upper()}]:")
            for line in categories[cat]:
                if total_count >= max_lines:
                    break
                output_lines.append(line)
                total_count += 1
        
        if len(self.registry) > total_count:
            output_lines.append(
                f"\n  ... ({len(self.registry) - total_count} more ops available; use /ops to list)"
            )
            
        return "\n".join(output_lines).strip()
