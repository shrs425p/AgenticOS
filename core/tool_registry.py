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

from tools import desktop_notifications as notifications
from tools import filesystem
from tools import screen_tools as screen
from tools import ocr_tools as ocr
from tools import terminal
from tools import web
from tools import system_tools

from core.runtime_config import DEFAULT_WORKSPACE
from core.url_presets import load_url_presets
from core.validators import validate_tool
from .guardrails import PathGuard
from core.tool_base import tool
from core.event_bus import OSEventBus

import importlib.util
import os
import sys
import logging



class ToolRegistry:
    def __init__(
        self,
        cfg: dict,
        memory_backend: Optional[Any] = None,
        confirm_handler: Optional[Callable] = None,
    ):
        self.cfg = cfg
        # Merge config-controlled policy surfaces. Code should expose capability;
        # config.yaml decides what is enabled, guarded, or restricted.
        self.rules = {
            **cfg.get("performance", {}),
            **cfg.get("system_control", {}),
            **cfg.get("security", {}),
            **cfg["rules"],
        }
        self.tools_cfg = cfg.get("tools", {})
        self._memory = memory_backend

        workspace = self.cfg.get("agent", {}).get("workspace", DEFAULT_WORKSPACE)
        self.fm = filesystem.FileManager(rules=self.rules, base_dir=workspace)
        self.term = terminal.TerminalExecutor(
            rules=self.rules,
            custom_keys=cfg.get("custom_keys", {}),
            cfg=self.cfg,
        )
        self.web = web.WebTools(rules=self.rules, base_dir=workspace, cfg=self.cfg)
        self.ui = notifications.NotificationCenter(rules=self.rules)
        self.screen = screen.ScreenManager(rules=self.rules, base_dir=workspace)
        self.ocr = ocr.OCRManager(rules=self.rules, base_dir=workspace, registry=self, cfg=self.cfg)
        self.sys_mgr = system_tools.SystemManager(rules=self.rules, cfg=self.cfg)
        self.event_bus = OSEventBus(cfg=self.cfg)
        self._notepad: List[str] = []
        self._canvas: str = ""
        self.registry: Dict[str, Dict[str, Any]] = {}
        self._register_all()
        self._load_plugins()  # <--- Load dynamic plugins
        self._workspace_root = Path(workspace).resolve()
        self.guard = PathGuard(cfg, on_confirm=confirm_handler)
        self.shadow_mode = False

    def _register_all(self):
        """Authoritative tool registration using dynamic inspection and URL presets."""
        # 1. Dynamic registration for core subsystems
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
        if self.tools_cfg.get("url_presets", True):
            for preset in load_url_presets(self.cfg):
                tool_name = preset.get("tool", "")
                mode = preset.get("mode", "direct")
                url = preset.get("url", "")
                desc = preset.get("desc", "Open preset URL.")
                if not tool_name or not url:
                    continue

                if mode == "direct":
                    def _mk_direct(u):
                        return lambda: self.term.open_url(u)
                    self._reg(tool_name, _mk_direct(url), desc)
                elif mode in ("query", "path"):
                    def _mk_value(u):
                        def _fn(value="", query="", url="", **_):
                            val = value or query or url or ""
                            v = urllib.parse.quote(val.strip())
                            return self.term.open_url(u.format(value=v))
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

    @tool(name="pref_set", category="Core")
    def _pref_set(self, key: str, value: str) -> str:
        if self._memory is not None and hasattr(self._memory, "set_preference"):
            self._memory.set_preference(key, value)
            return "OK"
        return (
            "Error: preferences storage not available (enable memory.backend=sqlite)."
        )

    @tool(name="pref_list", category="Core")
    def _pref_list(self) -> str:
        if self._memory is not None and hasattr(self._memory, "get_preferences"):
            prefs = self._memory.get_preferences()
            if not prefs:
                return "(no preferences)"
            return "\n".join(f"{k}={v}" for k, v in prefs.items())
        return (
            "Error: preferences storage not available (enable memory.backend=sqlite)."
        )

    @tool(name="register_commitment", desc="Track a future commitment or follow-up. Args: text, due_date (optional)", category="Core")
    def register_commitment(self, text: str, due_date: Optional[str] = None) -> str:
        """Register a commitment in the memory manager."""
        from core.memory_manager import get_memory_manager
        mm = get_memory_manager()
        if mm:
            return mm.register_commitment(text, due_date)
        return "Error: Memory manager not available."

    @tool(name="complete_commitment", desc="Mark a commitment as finished. Args: commitment_id", category="Core")
    def complete_commitment(self, commitment_id: str) -> str:
        """Mark a commitment as completed."""
        from core.memory_manager import get_memory_manager
        mm = get_memory_manager()
        if mm:
            return mm.complete_commitment(commitment_id)
        return "Error: Memory manager not available."

    def _load_plugins(self):
        """Scan tools/plugins/ (and subdirectories) for any .py files and register functions with @tool."""
        plugin_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "tools", "plugins"
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
                    full_mod_name = f"tools.plugins.{mod_path}"

                    if full_mod_name in sys.modules:
                        self._register_module_tools(sys.modules[full_mod_name])
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
                            self._register_module_tools(module)
                    except Exception:
                        logging.exception("[PLUGIN ERROR] Failed to load %s", file_path)

    def _register_module_tools(self, module, default_category="Plugins"):
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

    @tool(name="current_datetime", category="Core")
    def _now(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @tool(name="timestamp", category="Core")
    def _timestamp(self) -> str:
        return str(int(time.time()))

    @tool(name="note_add", category="Core")
    def _note_add(self, text: str) -> str:
        self._notepad.append(f"[{self._now()}] {text}")
        return f"Note saved. Total notes: {len(self._notepad)}"

    @tool(name="note_list", category="Core")
    def _note_list(self) -> str:
        if not self._notepad:
            return "Notepad is empty."
        return "\n".join(f"{i + 1}. {note}" for i, note in enumerate(self._notepad))

    @tool(name="note_clear", category="Core")
    def _note_clear(self) -> str:
        self._notepad.clear()
        return "Notepad cleared."

    @tool(name="canvas_set", category="Core")
    def _canvas_set(self, content: str) -> str:
        self._canvas = str(content)
        return "Canvas updated."

    @tool(name="canvas_append", category="Core")
    def _canvas_append(self, content: str) -> str:
        self._canvas += f"\n{content}"
        return "Canvas appended."

    @tool(name="canvas_view", category="Core")
    def _canvas_view(self) -> str:
        if not self._canvas:
            return "Canvas is empty."
        return self._canvas

    @tool(name="canvas_clear", category="Core")
    def _canvas_clear(self) -> str:
        self._canvas = ""
        return "Canvas cleared."

    @tool(name="tools_count", category="Core")
    def tools_count(self) -> str:
        """Return the authoritative count of currently registered tools."""
        return str(len(self.registry))

    @tool(name="tools_list", category="Core")
    def tools_list(self) -> str:
        """Return the authoritative list of currently registered tools (one per line)."""
        return "\n".join(sorted(self.registry.keys()))

    @tool(name="memory_search", category="Core")
    def memory_search(self, query: str, limit: int = 10) -> str:
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

    @tool(name="download_smart", category="Core")
    def download_smart(self, url: str, dest_path: str) -> str:
        """Download with retries/fallbacks and post-checks.

        Strategy:
        1) requests streaming download (no shell interpolation)
        2) built-in web.download_file fallback
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
            out = self.web.download_file(u, str(dst_path))
            attempts.append("web.download_file")
            if dst_path.exists() and dst_path.stat().st_size > 0:
                return (
                    out
                    + f"\nVALIDATION: downloaded via web.download_file (size={dst_path.stat().st_size})"
                )
            return out + "\nVALIDATION: download failed (file missing/empty)"
        except Exception as e:
            return f"Error: download failed after {attempts}: {type(e).__name__}: {e}"

    def call(self, name: str, args) -> str:
        if name not in self.registry:
            available = ", ".join(list(self.registry.keys())[:15])
            return f"Unknown tool: '{name}'. Available: {available}..."

        # ── Security Guardrails & Shadow Mode ─────────────────────────────────
        policy = self.cfg.get("policy", {})
        write_tools = set(policy.get("write_tools", [
            "write_file", "append_file", "delete_file", "create_dir", "delete_dir",
            "copy_file", "move_file", "edit_file", "edit_line", "insert_line",
            "replace_in_dir", "write_json", "write_csv", "touch", "run_command",
            "run_powershell", "run_script", "run_python", "pip_install", "npm_install",
            "git", "kill_process", "kill_process_by_name", "start_background",
            "hotkey", "press_key", "type_text", "mouse_click", "mouse_move"
        ]))

        # Shadow Mode Interception
        if self.shadow_mode and name in write_tools:
            return f"[SHADOW MODE] Dry run: would have executed '{name}' with args: {args}. Result simulated as SUCCESS."

        # ── Universal Path Guardrails ─────────────────────────────────────────
        # Automatically protect any argument that looks like a path
        path_keys = set(policy.get("path_keys", [
            "path", "src", "dst", "dest_path", "filename", "output_path", "directory"
        ]))
        read_only_tools = set(policy.get("read_only_tools", [
            "read_file", "list_dir", "file_info", "grep_file", "grep_dir",
            "read_json", "read_csv", "tree", "count_lines", "word_count",
            "file_exists", "file_hash"
        ]))

        if isinstance(args, dict):
            for key, val in args.items():
                if key.lower() in path_keys:
                    op = "read" if name in read_only_tools else "write"
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
                op = "read" if name in read_only_tools else "write"
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
                if isinstance(args, dict):
                    kwargs = {}
                    for p in params:
                        if p.name in args:
                            kwargs[p.name] = args[p.name]
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
                if name in write_tools:
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
                        self.term.pip_install(module_name)
                    except Exception:
                        import subprocess
                        subprocess.run([sys.executable, "-m", "pip", "install", module_name], capture_output=True)

                    importlib.invalidate_caches()
                    mod_name = fn.__module__
                    new_fn = fn
                    if mod_name and mod_name in sys.modules and mod_name.startswith("tools.plugins."):
                        try:
                            importlib.reload(sys.modules[mod_name])
                            new_fn = getattr(sys.modules[mod_name], fn.__name__)
                            self.registry[name]["fn"] = new_fn
                        except Exception as e:
                            logging.warning(f"Self-healing: Could not reload module {mod_name}: {e}")
                    return _invoke(new_fn)
                raise
            except FileNotFoundError as exc:
                if name in write_tools and name not in {"write_file", "write_json", "write_csv", "append_file"}:
                    raise

                # Exclude purely read operations from creating parent directories
                if name in read_only_tools:
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
        max_lines = int(self.cfg.get("prompts", {}).get("max_tool_descriptions", 140))
        
        # Group tools by category
        categories = {}
        for name, info in self.registry.items():
            cat = info.get("category", "General")
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(f"  {name}: {info['desc']}")

        # Build description string with headers
        output_lines = []
        total_count = 0
        
        # Prioritize core and high-value categories
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
                f"\n  ... ({len(self.registry) - total_count} more tools available; use /tools to list)"
            )
            
        return "\n".join(output_lines).strip()
