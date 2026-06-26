"""AgenticOs runtime orchestration."""

from datetime import datetime
import os
import platform
import random
import re
import subprocess
import sys
import time
import traceback
from typing import Callable, Dict, Optional, Tuple

import requests

try:
    import psutil
except ImportError:
    psutil = None

try:
    import readline
except ImportError:
    try:
        from pyreadline3 import Readline as _Readline

        readline = _Readline()
    except ImportError:
        readline = None

from kernel.audit import AuditLogger, infer_success
from kernel.context import ContextEngine
from kernel.log import get_logger
from kernel.memory import initialize_memory_manager, log_task_completion
from kernel.models import (
    DeepseekClient,
    GeminiClient,
    GithubClient,
    GroqClient,
    NvidiaClient,
    OllamaClient,
    OpenAIClient,
    OpenRouterClient,
    TieredClient,
)  # noqa: F401
from kernel.settings import (
    BASE_DIR,
    DEFAULT_SCAN_EXCLUDED_DIRS,
    DEFAULT_WORKSPACE,
    load_cfg,
)
from kernel.ui import (
    C,
    banner,
    has_final_answer,
    parse_actions,
    print_action,
    print_error,
    print_info,
    print_observation,
    print_success,
    print_warning,
    pulse_line,
    typewriter_print,
)
from kernel.store import SqliteSessionMemory
from kernel.tasks import TaskTracker
from kernel.registry import ToolRegistry
from kernel.version import DEFAULT_VERSION

logger = get_logger(__name__)


PROVIDER_CLIENT_MAP = {
    "ollama": "OllamaClient",
    "gemini": "GeminiClient",
    "groq": "GroqClient",
    "openai": "OpenAIClient",
    "openrouter": "OpenRouterClient",
    "nvidia": "NvidiaClient",
    "github": "GithubClient",
    "deepseek": "DeepseekClient",
}


from kernel.agent import Agent

class CommandCompleter:
    """Readline custom completer for AgenticOS CLI."""

    def __init__(self, commands, cli_instance):
        self.commands = sorted(list(commands))
        self.cli_instance = cli_instance
        self.choices = {
            "/zone": ["green", "yellow", "red", "blue", "1", "2", "3", "4"],
            "/logs": ["list", "tail", "show", "view"],
            "/tasks": ["list", "all", "current", "active", "show"],
            "/thinking": [
                "hide",
                "off",
                "false",
                "disable",
                "show",
                "on",
                "true",
                "enable",
            ],
        }

    def complete(self, text: str, state: int) -> Optional[str]:
        """Complete method for readline."""
        try:
            if not readline:
                return None
            buffer = readline.get_line_buffer()
            words = buffer.lstrip().split()

            # Scenario A: No words typed yet, or typing the first word (the command)
            if not words or (len(words) == 1 and not buffer.endswith(" ")):
                options = [cmd for cmd in self.commands if cmd.startswith(text)]
                if state < len(options):
                    return options[state]
                return None

            # Scenario B: Command already typed, typing the arguments
            base_cmd = words[0].lower()
            is_second_word = (len(words) == 1 and buffer.endswith(" ")) or (
                len(words) == 2 and not buffer.endswith(" ")
            )

            # Autocomplete sub-arguments
            if is_second_word and base_cmd in self.choices:
                sub_choices = self.choices[base_cmd]
                options = [opt for opt in sub_choices if opt.startswith(text)]
                if state < len(options):
                    return options[state]
                return None

            # Dynamic completion for provider choice
            if is_second_word and base_cmd == "/provider":
                providers = ["ollama"]
                if self.cli_instance and hasattr(self.cli_instance, "cfg"):
                    cloud_cfg = self.cli_instance.cfg.get("cloud", {})
                    if isinstance(cloud_cfg, dict):
                        providers.extend(cloud_cfg.keys())
                options = [opt for opt in providers if opt.startswith(text)]
                if state < len(options):
                    return options[state]
                return None

            # Scenario C: File/directory path autocompletion fallback
            import os

            norm_text = text.replace("\\", "/")
            if "/" in norm_text:
                search_dir, prefix = norm_text.rsplit("/", 1)
                if search_dir == "":
                    search_dir = "/"
            else:
                search_dir = "."
                prefix = norm_text

            try:
                if os.path.isdir(search_dir):
                    entries = os.listdir(search_dir)
                    options = []
                    for entry in entries:
                        if entry.startswith(prefix):
                            full_path = os.path.join(search_dir, entry)
                            if search_dir == ".":
                                disp = entry
                            elif search_dir == "/":
                                disp = "/" + entry
                            else:
                                original_dir = text.replace("\\", "/").rsplit("/", 1)[0]
                                if "\\" in text and "/" not in text:
                                    disp = (
                                        original_dir.replace("/", "\\") + "\\" + entry
                                    )
                                else:
                                    disp = original_dir + "/" + entry

                            if os.path.isdir(full_path):
                                disp += (
                                    "\\" if "\\" in text and "/" not in text else "/"
                                )
                            options.append(disp)

                    options.sort()
                    if state < len(options):
                        return options[state]
            except Exception:
                pass

            return None
        except Exception:
            return None


# ── CLI ───────────────────────────────────────────────────────────────────────
class CLI:
    COMMANDS = {
        "/help": "Show this help",
        "/model": "Switch current model",
        "/provider": "Switch provider (ollama/nvidia)",
        "/models": "List available models",
        "/ops": "List all available ops",
        "/tool_report": "Write a markdown tool report into workspace (tool_report.md)",
        "/doctor": "Run quick health checks (cfg, memory db, logs, provider)",
        "/ops_md": "Write manuals/ops_reference.md (tool name + description)",
        "/memory": "Show session memory summary",
        "/clear": "Clear session memory",
        "/reload": "Manually reload ops",
        "/cfg": "Open configuration folder in file explorer",
        "/history": "Show conversation history",
        "/version": "Show version info",
        "/shadow": "Toggle Shadow Mode (Dry Run)",
        "/thinking": "Toggle verbose model thinking trace (Show/Hide)",
        "/zone": "Toggle security zone (green/yellow/red/blue) or pass a zone name to switch directly",
        "/logs": "Open logs folder or display recent logs (use '/logs tail')",
        "/tasks": "List all session tasks or show the active task progress (use '/tasks current')",
        "/sysinfo": "Display system resources and agent health dashboard (CPU, RAM, Disk, Uptime)",
        "/exit": "Exit AgenticOs",
    }

    def __init__(self, dry_run: bool = False):
        self.cfg = load_cfg()
        self.agent = Agent(self.cfg, confirm_handler=self.handle_security_confirmation)
        self.running = True
        if dry_run:
            self.agent.ops.shadow_mode = True
            print(f"\n{C.YELLOW}Shadow Mode (Dry Run) is ON{C.RESET}")

    def handle_security_confirmation(self, path: str, operation: str) -> bool:
        """Confirm action with user (CLI implementation)."""
        if (
            self.cfg.get("agent", {}).get("auto_confirm") is True
            or self.cfg.get("autonomy", {}).get("autopilot") is True
        ):
            logger.info(f"Auto-confirming security action: {operation} on '{path}'")
            return True
        logger.info(f"\n{C.ROSE}▲ STOP — SECURITY GUARDRAIL{C.RESET}")
        logger.info(
            f"The agent is attempting a {C.BOLD}{operation.upper()}{C.RESET} action outside the workspace."
        )
        logger.info(f"Target Path: {C.TEAL}{path}{C.RESET}")
        logger.info(
            f"{C.SLATE}(You can allow this once, or modify cfg.yaml to change security rules){C.RESET}"
        )
        try:
            ans = input("\nDo you allow this specific action? [y/N]: ").strip().lower()
            return ans == "y"
        except (KeyboardInterrupt, EOFError):
            return False

    def select_provider(self, force: bool = False):
        """select_provider function."""
        providers = ["ollama"] + list(self.cfg.get("cloud", {}).keys())
        current = (self.cfg.get("agent", {}).get("provider") or "ollama").lower()

        logger.info(f"\n{C.CYAN}{C.BOLD}Providers:{C.RESET}")
        for i, p in enumerate(providers, 1):
            marker = f" {C.GREEN}◀ current{C.RESET}" if p == current else ""
            logger.info(f"  {C.BOLD}{i}.{C.RESET} {p}{marker}")
        if not force:
            logger.info(f"\n  {C.BOLD}0.{C.RESET} Keep current ({current})")

        while True:
            try:
                limit = len(providers)
                prompt = (
                    f"\n{C.CYAN}Select provider [0-{limit}]: {C.RESET}"
                    if not force
                    else f"\n{C.CYAN}Select provider [1-{limit}]: {C.RESET}"
                )
                raw = input(prompt).strip()
                if not raw and not force:
                    return
                idx = int(raw)
                if idx == 0 and not force:
                    return
                if 1 <= idx <= len(providers):
                    chosen = providers[idx - 1]
                    self.cfg.setdefault("agent", {})["provider"] = chosen
                    self.agent = Agent(self.cfg)
                    print_success(f"Provider set to: {chosen}")
                    return
                else:
                    print_error(
                        f"Invalid selection: {idx} is out of range [1-{limit}]."
                    )
            except ValueError:
                print_error("Selection required: Please enter a valid integer.")
                if not force:
                    return
            except (KeyboardInterrupt, EOFError):
                if not force:
                    return
                print_error("Selection required: Interrupted.")

    def select_model(self, force=False):
        """select_model function."""
        models = self.agent.client.list_models()
        if not models:
            provider_name = self.agent.client.provider.capitalize()
            print_error(f"No models found for {provider_name}.")
            return

        err = getattr(self.agent.client, "last_list_error", "")
        if err and self.agent.client.provider == "nvidia":
            print_warning(
                f"Could not fully list Nvidia models ({err}). Showing fallback list."
            )

        logger.info(
            f"\n{C.CYAN}{C.BOLD}Available {self.agent.client.provider.capitalize()} Models:{C.RESET}"
        )
        for i, m in enumerate(models, 1):
            marker = (
                f" {C.GREEN}◀ current{C.RESET}" if m == self.agent.client.model else ""
            )
            logger.info(f"  {C.BOLD}{i}.{C.RESET} {m}{marker}")

        if not force:
            logger.info(
                f"\n  {C.BOLD}0.{C.RESET} Keep current ({self.agent.client.model})"
            )

        # Always show locally installed Ollama models (read-only) for convenience.
        try:
            if self.agent.client.provider != "ollama":
                base_url = self.cfg.get("ollama", {}).get("base_url")
                if not base_url:
                    return
                timeout = self.cfg.get("timeouts", {}).get("list_models", 5)
                resp = requests.get(f"{base_url}/api/tags", timeout=timeout)
                resp.raise_for_status()
                ollama_models = [
                    m.get("name", "")
                    for m in (resp.json() or {}).get("models", [])
                    if m.get("name")
                ]
                if ollama_models:
                    logger.info(f"\n{C.DIM}Installed Ollama Models (local):{C.RESET}")
                    for m in ollama_models[:60]:
                        logger.info(f"  {m}")
                    if len(ollama_models) > 60:
                        logger.info(
                            f"  {C.DIM}... ({len(ollama_models) - 60} more){C.RESET}"
                        )
        except (RuntimeError, OSError) as e:
            print_warning(f"Warning: Failed to list models: {e}")

        while True:
            try:
                limit = len(models)
                prompt = (
                    f"\n{C.CYAN}Select model [0-{limit}]: {C.RESET}"
                    if not force
                    else f"\n{C.CYAN}Select model [1-{limit}]: {C.RESET}"
                )
                raw = input(prompt).strip()
                if not raw and not force:
                    break
                idx = int(raw)
                if idx == 0 and not force:
                    break
                if 1 <= idx <= len(models):
                    self.agent.client.model = models[idx - 1]
                    print_success(f"Model set to: {self.agent.client.model}")
                    break
                else:
                    print_error(
                        f"Invalid selection: {idx} is out of range [1-{limit}]."
                    )
            except ValueError:
                print_error("Selection required: Please enter a valid integer.")
                if not force:
                    break
            except (KeyboardInterrupt, EOFError):
                if not force:
                    break
                print_error("Selection required: Interrupted.")

    def handle_command(self, cmd: str):
        """handle_command function."""
        parts = cmd.strip().split(None, 1)
        base = parts[0].lower()

        if base == "/help":
            logger.info(f"\n{C.CYAN}{C.BOLD}AgenticOs Commands:{C.RESET}")
            for c, d in self.COMMANDS.items():
                logger.info(f"  {C.YELLOW}{c:<12}{C.RESET} {d}")

        elif base == "/model":
            self.select_model()

        elif base == "/provider":
            self.select_provider()

        elif base == "/models":
            models = self.agent.client.list_models()
            if models:
                logger.info(f"\n{C.CYAN}Available models:{C.RESET}")
                for m in models:
                    active = (
                        f" {C.GREEN}◀ active{C.RESET}"
                        if m == self.agent.client.model
                        else ""
                    )
                    logger.info(f"  {m}{active}")
            else:
                err = getattr(self.agent.client, "last_list_error", "")
                if err:
                    print_error(f"No models found. ({err})")
                else:
                    print_error("No models found.")

        elif base == "/ops":
            logger.info(
                f"\n{C.CYAN}{C.BOLD}Available Tools ({len(self.agent.ops.registry)}):{C.RESET}"
            )
            for name, info in self.agent.ops.registry.items():
                logger.info(
                    f"  {C.YELLOW}{name:<25}{C.RESET} {C.DIM}{info['desc']}{C.RESET}"
                )

        elif base == "/tool_report":
            # Authoritative: read directly from the registry, not from the truncated prompt.
            ops = sorted(self.agent.ops.registry.keys())
            lines = [
                "# Tool Report",
                "",
                f"**Total ops:** {len(ops)}",
                "",
            ]
            lines += [f"{i}. {name}" for i, name in enumerate(ops, 1)]
            lines.append("")
            out = self.agent.ops.fm.write_file("tool_report.md", "\n".join(lines))
            print_success(out)
            print_info(
                f"Wrote: {C.BOLD}{self.cfg['agent'].get('workspace', DEFAULT_WORKSPACE)}\\tool_report.md{C.RESET}"
            )

        elif base == "/ops_md":
            try:
                ops = sorted(
                    self.agent.ops.registry.items(), key=lambda kv: kv[0].lower()
                )
                out_dir = os.path.join(BASE_DIR, "manuals")
                os.makedirs(out_dir, exist_ok=True)
                out_path = os.path.join(out_dir, "ops_reference.md")

                lines = []
                lines.append("# Tools Reference")
                lines.append("")
                lines.append(
                    f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
                lines.append(f"Total ops: {len(ops)}")
                lines.append("")
                lines.append("| Tool | Description |")
                lines.append("| --- | --- |")
                for name, info in ops:
                    desc = str((info or {}).get("desc", "")).strip().replace("\n", " ")
                    desc = desc.replace("|", "\\|")
                    lines.append(f"| `{name}` | {desc} |")
                lines.append("")

                with open(out_path, "w", encoding="utf-8") as handle:
                    handle.write("\n".join(lines))
                print_success(f"Wrote: {out_path}")
            except Exception as e:
                print_error(f"Failed to write ops_reference.md: {e}")

        elif base == "/doctor":
            logger.info(f"\n{C.CYAN}{C.BOLD}Doctor Checks:{C.RESET}")
            # 1) Config parse already succeeded if we got here.
            print_success("cfg.yaml: OK (parsed)")
            # 2) Memory backend writable?
            try:
                mem = self.agent.memory
                if hasattr(mem, "healthcheck"):
                    logger.info(mem.healthcheck())
                else:
                    print_success("memory: OK")
            except Exception as e:
                print_error(f"memory: Error: {e}")
            # 3) Audit dir writable?
            try:
                audit_dir = (
                    getattr(self.agent, "audit", None).log_dir
                    if hasattr(self.agent, "audit")
                    else ""
                )
                if audit_dir:
                    import os as _os

                    testp = _os.path.join(audit_dir, ".__doctor_write_test")
                    with open(testp, "w", encoding="utf-8") as h:
                        h.write("ok")
                    _os.remove(testp)
                    print_success(f"audit_dir writable: {audit_dir}")
                else:
                    print_warning("audit: not enabled")
            except Exception as e:
                print_error(f"audit_dir writable: Error: {e}")
            # 4) Provider connectivity (list_models)
            try:
                models = self.agent.client.list_models()
                if models:
                    print_success(
                        f"provider '{self.agent.client.provider}': OK ({len(models)} model(s) visible)"
                    )
                else:
                    err = getattr(self.agent.client, "last_list_error", "")
                    print_warning(
                        f"provider '{self.agent.client.provider}': no models ({err})"
                    )
            except Exception as e:
                print_error(f"provider check: Error: {e}")

        elif base == "/memory":
            logger.info(
                f"\n{C.CYAN}Session Memory:{C.RESET}\n{self.agent.memory.summary()}"
            )

        elif base == "/clear":
            self.agent.memory.clear()
            print_success("Session memory cleared.")

        elif base == "/shadow":
            self.agent.ops.shadow_mode = not self.agent.ops.shadow_mode
            status = (
                f"{C.GREEN}ON{C.RESET}"
                if self.agent.ops.shadow_mode
                else f"{C.RED}OFF{C.RESET}"
            )
            print_info(f"Shadow Mode (Dry Run) is now {status}")

        elif base == "/thinking":
            arg = parts[1].strip().lower() if len(parts) > 1 else ""
            current = self.cfg.get("agent", {}).get("verbose_thinking", False)
            if arg in ("hide", "off", "false", "disable"):
                new_val = False
            elif arg in ("show", "on", "true", "enable"):
                new_val = True
            else:
                new_val = not current
            self.cfg.setdefault("agent", {})["verbose_thinking"] = new_val
            self.verbose = new_val
            status = f"{C.GREEN}ON{C.RESET}" if new_val else f"{C.RED}OFF{C.RESET}"
            print_info(f"Verbose model thinking trace is now {status}")

        elif base == "/reload":
            self.agent.mtimes = {}  # Force reload
            self.agent.check_reload()

        elif base == "/tasks":
            arg = parts[1].strip().lower() if len(parts) > 1 else "list"
            tasks = getattr(self.task_tracker, "tasks", [])
            current_task = getattr(self.task_tracker, "current", None)

            if not tasks:
                print_info("No tasks recorded in the active session.")
            elif arg in ("list", "all"):
                logger.info(
                    f"\n{C.CYAN}Active Session Tasks ({len(tasks)} tasks):{C.RESET}"
                )
                for idx, task in enumerate(tasks, 1):
                    status = task.get("status", "unknown").lower()
                    is_curr = task is current_task

                    if status == "completed":
                        badge = f"{C.EMERALD}[COMPLETED]{C.RESET}"
                    elif status == "failed":
                        badge = f"{C.ROSE}[FAILED]{C.RESET}"
                    elif status == "running":
                        badge = f"{C.TEAL}[RUNNING]{C.RESET}"
                    else:
                        badge = f"{C.SLATE}[{status.upper()}]{C.RESET}"

                    goal = task.get("goal", "").replace("\n", " ")
                    if len(goal) > 55:
                        goal = goal[:52] + "..."

                    curr_marker = f" {C.PURPLE}(current){C.RESET}" if is_curr else ""
                    iter_info = (
                        f" (Iteration: {task.get('iteration', 0)})"
                        if status == "running"
                        else ""
                    )
                    logger.info(
                        f"  {C.BOLD}#{idx:<3}{C.RESET} {badge:<22} {goal}{curr_marker}{iter_info}"
                    )
            elif arg in ("current", "active", "show"):
                if not current_task:
                    print_info("No active task is currently running.")
                else:
                    status = current_task.get("status", "unknown").lower()
                    if status == "completed":
                        badge = f"{C.EMERALD}[COMPLETED]{C.RESET}"
                    elif status == "failed":
                        badge = f"{C.ROSE}[FAILED]{C.RESET}"
                    elif status == "running":
                        badge = f"{C.TEAL}[RUNNING]{C.RESET}"
                    else:
                        badge = f"{C.SLATE}[{status.upper()}]{C.RESET}"

                    logger.info(f"\n{C.CYAN}Current Task Details:{C.RESET}")
                    logger.info(
                        f"  {C.BOLD}Goal:{C.RESET} {current_task.get('goal', 'Untitled')}"
                    )
                    logger.info(f"  {C.BOLD}Status:{C.RESET} {badge}")
                    logger.info(
                        f"  {C.BOLD}Iteration:{C.RESET} {current_task.get('iteration', 0)}"
                    )
                    logger.info(
                        f"  {C.BOLD}Current Step:{C.RESET} {C.AMBER}{current_task.get('current_step', 'None')}{C.RESET}"
                    )

                    plan = current_task.get("plan", [])
                    current_step = current_task.get("current_step", "")
                    if plan:
                        logger.info(f"\n  {C.BOLD}Plan & Progress:{C.RESET}")
                        found_curr = False
                        for i, step in enumerate(plan, 1):
                            is_step_curr = step == current_step or (
                                current_step and current_step in step
                            )
                            if is_step_curr:
                                marker = f"{C.AMBER}[/]{C.RESET}"
                                step_text = f"{C.BOLD}{C.AMBER}{step}{C.RESET}"
                                found_curr = True
                            elif found_curr:
                                marker = "[ ]"
                                step_text = f"{C.SLATE}{step}{C.RESET}"
                            else:
                                marker = f"{C.EMERALD}[x]{C.RESET}"
                                step_text = f"{C.DIM}{C.SLATE}{step}{C.RESET}"
                            logger.info(f"    {marker} {i}. {step_text}")

                    last_act = current_task.get("last_action", "")
                    if last_act:
                        logger.info(f"\n  {C.BOLD}Last Action:{C.RESET} {last_act}")

                    last_obs = current_task.get("last_observation", "")
                    if last_obs:
                        preview_obs = last_obs.replace("\n", " ")
                        if len(preview_obs) > 120:
                            preview_obs = preview_obs[:117] + "..."
                        logger.info(
                            f"  {C.BOLD}Last Observation:{C.RESET} {C.DIM}{preview_obs}{C.RESET}"
                        )
            else:
                print_error(
                    f"Unknown tasks option: '{arg}'. Valid options: list, current."
                )

        elif base == "/cfg":
            cfg_dir = os.path.join(BASE_DIR, "cfg")
            logger.info(f"\n{C.CYAN}Opening cfg folder: {cfg_dir}{C.RESET}")
            if not os.path.exists(cfg_dir):
                print_error(f"Config directory does not exist: {cfg_dir}")
            else:
                try:
                    if sys.platform == "win32":
                        os.startfile(cfg_dir)  # noqa: S606
                    elif sys.platform == "darwin":
                        subprocess.Popen(["open", cfg_dir])  # nosec B605
                    else:
                        subprocess.Popen(["xdg-open", cfg_dir])  # nosec B605
                    print_success("Config folder opened successfully.")
                except Exception as e:
                    print_error(f"Failed to open cfg folder: {e}")

        elif base == "/history":
            msgs = self.agent.memory.get_messages()
            logger.info(
                f"\n{C.CYAN}Conversation History ({len(msgs)} messages):{C.RESET}"
            )
            for msg in msgs[-20:]:
                role = msg["role"].upper()
                color = C.BLUE if role == "USER" else C.GREEN
                preview = msg["content"][:200].replace("\n", " ")
                logger.info(
                    f"  {color}{C.BOLD}{role:<12}{C.RESET} {C.DIM}{preview}{C.RESET}"
                )

        elif base == "/version":
            provider = self.agent.client.provider
            version_str = DEFAULT_VERSION
            try:
                changelog_path = os.path.join(BASE_DIR, "CHANGELOG.md")
                if os.path.exists(changelog_path):
                    with open(changelog_path, "r", encoding="utf-8") as f:
                        for line in f:
                            if line.startswith("## "):
                                match = re.search(
                                    r"\[?([0-9]+\.[0-9]+\.[0-9]+(?:-[a-zA-Z0-9.]+)*)\]?",
                                    line,
                                )
                                if match:
                                    version_str = match.group(1)
                                    break
            except Exception:
                pass
            logger.info(f"\n{C.CYAN}AgenticOs v{version_str}{C.RESET}")
            logger.info(f"  Provider : {provider}")
            logger.info(f"  Model    : {self.agent.client.model}")
            if hasattr(self.agent.client, "base_url"):
                logger.info(f"  Endpoint : {self.agent.client.base_url}")
            logger.info(f"  Tools    : {len(self.agent.ops.registry)}")
            logger.info(f"  Session  : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        elif base == "/logs":
            log_dir = os.path.join(BASE_DIR, "data", "logs")

            def resolve_log_path(name: str) -> Optional[str]:
                if os.path.isabs(name) and os.path.exists(name):
                    return name
                if os.path.exists(name):
                    return os.path.abspath(name)

                search_folders = []
                if os.path.exists(log_dir):
                    search_folders.append(log_dir)
                memory_dir = os.path.join(self.agent.workspace, "memory")
                if os.path.exists(memory_dir):
                    search_folders.append(memory_dir)

                for folder in search_folders:
                    p = os.path.join(folder, name)
                    if os.path.exists(p):
                        return p

                for folder in search_folders:
                    for r, _, files in os.walk(folder):
                        for f in files:
                            if name.lower() in f.lower() or f.lower().startswith(
                                name.lower()
                            ):
                                return os.path.join(r, f)
                return None

            def format_and_print_lines(lines, start_idx=1):
                for idx, line in enumerate(lines, start_idx):
                    clean_line = line.rstrip("\n")
                    line_colored = clean_line

                    if any(
                        k in line_colored.lower()
                        for k in ("completed", "✓", "success", "ok", "green")
                    ):
                        line_colored = re.sub(
                            r"(completed|✓|success|ok|green)",
                            f"{C.EMERALD}\\1{C.RESET}",
                            line_colored,
                            flags=re.IGNORECASE,
                        )
                    if any(
                        k in line_colored.lower()
                        for k in ("failed", "error", "exception", "red", "rose")
                    ):
                        line_colored = re.sub(
                            r"(failed|error|exception|red|rose)",
                            f"{C.ROSE}\\1{C.RESET}",
                            line_colored,
                            flags=re.IGNORECASE,
                        )
                    if any(
                        k in line_colored.lower()
                        for k in (
                            "running",
                            "info",
                            "warning",
                            "thinking",
                            "yellow",
                            "amber",
                            "teal",
                        )
                    ):
                        line_colored = re.sub(
                            r"(running|info|warning|thinking|yellow|amber|teal)",
                            f"{C.AMBER}\\1{C.RESET}",
                            line_colored,
                            flags=re.IGNORECASE,
                        )

                    line_colored = re.sub(
                        r"(\d{4}-\d{2}-\d{2}(?:\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?)?)",
                        f"{C.CYAN}\\1{C.RESET}",
                        line_colored,
                    )

                    prefix = f"{C.DIM}{C.SLATE}{idx:>4} │ {C.RESET}"
                    print(f"{prefix}{line_colored}")

            if len(parts) > 1 and parts[1].strip().lower().split()[0] == "list":
                logger.info(
                    f"\n{C.CYAN}{C.BOLD}AGENTIC OS • Log & Memory Directory{C.RESET}"
                )
                logger.info(
                    f"{C.SLATE}──────────────────────────────────────────────────────────────────────────{C.RESET}"
                )
                logger.info(
                    f"  {C.BOLD}{'#':<3} {'Relative Path':<40} {'Size':<10} {'Last Modified':<16}{C.RESET}"
                )
                logger.info(
                    f"{C.SLATE}──────────────────────────────────────────────────────────────────────────{C.RESET}"
                )

                found_files = []
                memory_dir = os.path.join(self.agent.workspace, "memory")
                for folder in (log_dir, memory_dir):
                    if os.path.exists(folder):
                        for root, _, files in os.walk(folder):
                            for f in files:
                                if f.endswith(
                                    (".log", ".txt", ".md", ".json")
                                ) and not f.startswith("."):
                                    full_path = os.path.join(root, f)
                                    rel_path = os.path.relpath(
                                        full_path, self.agent.workspace
                                    ).replace("\\", "/")
                                    size_bytes = os.path.getsize(full_path)
                                    mtime = os.path.getmtime(full_path)
                                    found_files.append(
                                        (rel_path, full_path, size_bytes, mtime)
                                    )

                found_files.sort(key=lambda x: x[3], reverse=True)

                if not found_files:
                    logger.info("  No logs or memory files recorded yet.")
                else:
                    for idx, (rel_path, full_path, size_bytes, mtime) in enumerate(
                        found_files, 1
                    ):
                        dt = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
                        if size_bytes < 1024:
                            size_str = f"{size_bytes} B"
                        elif size_bytes < 1024 * 1024:
                            size_str = f"{size_bytes / 1024:.1f} KB"
                        else:
                            size_str = f"{size_bytes / (1024 * 1024):.1f} MB"

                        disp_path = rel_path
                        if len(disp_path) > 40:
                            disp_path = "..." + disp_path[-37:]

                        logger.info(
                            f"  {C.BOLD}{idx:<3}{C.RESET} {C.TEAL}{disp_path:<40}{C.RESET} {C.SLATE}{size_str:<10}{C.RESET} {C.PURPLE}{dt:<16}{C.RESET}"
                        )
                logger.info(
                    f"{C.SLATE}──────────────────────────────────────────────────────────────────────────{C.RESET}"
                )

            elif len(parts) > 1 and parts[1].strip().lower().split()[0] in (
                "tail",
                "show",
                "view",
            ):
                subparts = parts[1].strip().split()
                sub = subparts[0].lower()
                rem = subparts[1:]

                target_name = "agenticos.log"
                num_lines = 20

                if len(rem) == 1:
                    if rem[0].isdigit():
                        num_lines = int(rem[0])
                    else:
                        target_name = rem[0]
                elif len(rem) >= 2:
                    if rem[-1].isdigit():
                        num_lines = int(rem[-1])
                        target_name = " ".join(rem[:-1])
                    else:
                        target_name = " ".join(rem)

                resolved_file = resolve_log_path(target_name)
                if not resolved_file:
                    print_error(
                        f"Could not find any log or memory file matching: '{target_name}'"
                    )
                else:
                    try:
                        with open(
                            resolved_file, "r", encoding="utf-8", errors="replace"
                        ) as f:
                            lines = f.readlines()

                        total_lines = len(lines)
                        if sub == "tail":
                            slice_lines = lines[-num_lines:]
                            start_idx = max(1, total_lines - num_lines + 1)
                            label_str = f"Last {len(slice_lines)} entries (tail)"
                        else:
                            slice_lines = lines[:num_lines]
                            start_idx = 1
                            label_str = f"First {len(slice_lines)} entries ({sub})"

                        rel_path = os.path.relpath(
                            resolved_file, self.agent.workspace
                        ).replace("\\", "/")
                        logger.info(
                            f"\n{C.CYAN}{C.BOLD}{label_str} from {rel_path}:{C.RESET}"
                        )
                        logger.info(
                            f"{C.SLATE}────────────────────────────────────────────────────────────────────────{C.RESET}"
                        )
                        if not slice_lines:
                            logger.info("  [Empty file or range]")
                        else:
                            format_and_print_lines(slice_lines, start_idx)
                        logger.info(
                            f"{C.SLATE}────────────────────────────────────────────────────────────────────────{C.RESET}"
                        )
                    except Exception as e:
                        print_error(f"Failed to read file: {e}")
            else:
                logger.info(f"\n{C.CYAN}Opening logs folder: {log_dir}{C.RESET}")
                if not os.path.exists(log_dir):
                    print_error(f"Logs directory does not exist: {log_dir}")
                else:
                    try:
                        if sys.platform == "win32":
                            os.startfile(log_dir)  # noqa: S606
                        elif sys.platform == "darwin":
                            subprocess.Popen(["open", log_dir])  # nosec B605
                        else:
                            subprocess.Popen(["xdg-open", log_dir])  # nosec B605
                        print_success("Logs folder opened successfully.")
                    except Exception as e:
                        print_error(f"Failed to open logs folder: {e}")

        elif base in ("/exit", "/quit", "/q"):
            try:
                # Do NOT wipe persistent memory on exit. Use /clear for that.
                if not bool(self.cfg.get("memory", {}).get("enable_persistence", True)):
                    self.agent.memory.clear()
                    logger.info(f"\n{C.CYAN}Goodbye. Session memory wiped.{C.RESET}")
                else:
                    logger.info(f"\n{C.CYAN}Goodbye.{C.RESET}")
            except (IOError, OSError, ValueError) as e:
                print_warning(f"Warning: Error during exit cleanup: {e}")
                logger.info(f"\n{C.CYAN}Goodbye.{C.RESET}")
            try:
                if hasattr(self.agent, "audit"):
                    self.agent.audit.session_end(
                        getattr(self.agent, "session_id", "unknown"), status="exit"
                    )
            except (IOError, OSError) as e:
                print_warning(f"Warning: Failed to log audit session end: {e}")
            self.running = False

        elif base == "/zone":
            guard = getattr(getattr(self.agent, "ops", None), "guard", None)
            if guard is None:
                print_error("PathGuard is not available on the current agent.")
                return

            # Zone configurations: (name, enabled, require_hitm, read_only)
            #   green  → guard ON + HITM required       (strictest sandbox)
            #   yellow → guard ON, no HITM              (autonomous outside workspace)
            #   red    → guard OFF                      (fully unrestricted)
            #   blue   → guard ON, all writes blocked   (read-only / audit mode)
            ZONE_STATES = [
                ("green", True, True, False),
                ("yellow", True, False, False),
                ("red", False, False, False),
                ("blue", True, False, True),
            ]

            # Numeric aliases: 1=green, 2=yellow, 3=red, 4=blue
            ALIASES = {"1": "green", "2": "yellow", "3": "red", "4": "blue"}

            arg = (parts[1].strip().lower() if len(parts) > 1 else "") or ""
            arg = ALIASES.get(arg, arg)

            if arg and arg not in (z[0] for z in ZONE_STATES):
                print_error(
                    f"Unknown zone: '{arg}'. "
                    "Valid options: green, yellow, red, blue (or 1, 2, 3, 4)."
                )
                return

            if arg:
                target = next(z for z in ZONE_STATES if z[0] == arg)
            else:
                # Sequential toggle: match current guard state to find index
                current_enabled = guard.enabled
                current_hitm = guard.require_hitm
                current_readonly = getattr(guard, "read_only", False)
                current_idx = 0
                for i, (_, en, hm, ro) in enumerate(ZONE_STATES):
                    if (
                        en == current_enabled
                        and hm == current_hitm
                        and ro == current_readonly
                    ):
                        current_idx = i
                        break
                target = ZONE_STATES[(current_idx + 1) % len(ZONE_STATES)]

            zone_name, zone_enabled, zone_hitm, zone_readonly = target

            # Apply to live PathGuard instance immediately
            guard.enabled = zone_enabled
            guard.require_hitm = zone_hitm
            guard.read_only = zone_readonly

            # Colour per zone
            ZONE_COLORS = {
                "green": C.EMERALD,
                "yellow": C.AMBER,
                "red": C.ROSE,
                "blue": C.BLUE,
            }
            zone_color = ZONE_COLORS.get(zone_name, C.SLATE)

            # Status labels
            guard_label = (
                f"{C.EMERALD}ENABLED{C.RESET}"
                if zone_enabled
                else f"{C.ROSE}DISABLED{C.RESET}"
            )
            hitm_label = (
                f"{C.AMBER}ON — write outside workspace requires approval{C.RESET}"
                if zone_hitm
                else f"{C.EMERALD}OFF — fully autonomous{C.RESET}"
            )
            ro_label = (
                f"{C.BLUE}ON — all writes and deletes blocked globally{C.RESET}"
                if zone_readonly
                else f"{C.SLATE}OFF{C.RESET}"
            )

            logger.info(
                f"\n{zone_color}{C.BOLD}◆ Zone switched → {zone_name.upper()} ZONE{C.RESET}"
            )
            logger.info(f"  PathGuard  : {guard_label}")
            logger.info(f"  HITM       : {hitm_label}")
            logger.info(f"  Read-Only  : {ro_label}")

            zone_desc = {
                "green": "Workspace-only autonomy. Writes outside workspace require human approval.",
                "yellow": "PathGuard active. Outside-workspace modifications allowed autonomously.",
                "red": "PathGuard disabled. Agent has unrestricted filesystem access.",
                "blue": "Audit / read-only mode. All write and delete operations blocked system-wide.",
            }
            logger.info(f"  {C.DIM}{zone_desc[zone_name]}{C.RESET}")

        elif base == "/sysinfo":
            logger.info(
                f"\n  {C.TEAL}{C.BOLD}◆ AgenticOS System Telemetry & Health Dashboard{C.RESET}"
            )
            logger.info(
                f"  {C.SLATE}──────────────────────────────────────────────────────────────────────{C.RESET}"
            )
            try:
                if psutil is None:
                    raise ImportError("psutil package is not installed")

                # 1. OS & Uptime
                os_name = platform.system()
                os_release = platform.release()
                os_arch = platform.machine()
                py_ver = platform.python_version()

                uptime_secs = time.time() - psutil.boot_time()
                hours, remainder = divmod(uptime_secs, 3600)
                minutes, seconds = divmod(remainder, 60)
                uptime_str = f"{int(hours)}h {int(minutes)}m {int(seconds)}s"

                # 2. Helper for colored progress bar
                def make_bar(percent: float, width: int = 15) -> str:
                    filled = int(round((percent / 100.0) * width))
                    if percent < 60:
                        color = C.EMERALD
                    elif percent < 85:
                        color = C.AMBER
                    else:
                        color = C.ROSE
                    bar = f"{color}{'■' * filled}{C.RESET}{C.SLATE}{'·' * (width - filled)}{C.RESET}"
                    return bar

                # 3. CPU Load
                cpu = psutil.cpu_percent(interval=0.1)
                cpu_bar = make_bar(cpu)

                # 4. RAM
                mem = psutil.virtual_memory()
                mem_used_mb = mem.used // (1024**2)
                mem_total_mb = mem.total // (1024**2)
                mem_bar = make_bar(mem.percent)

                # 5. Disk
                disk = psutil.disk_usage("/")
                disk_free_gb = disk.free // (1024**3)
                disk_total_gb = disk.total // (1024**3)
                disk_bar = make_bar(disk.percent)

                # 6. Agent Process Stats
                pid = os.getpid()
                proc = psutil.Process(pid)
                proc_mem_mb = proc.memory_info().rss // (1024**2)

                # 7. GPU Telemetry
                gpus = []
                import shutil
                import json

                nv_smi = shutil.which("nvidia-smi")
                if nv_smi:
                    try:
                        res = subprocess.run(
                            [
                                nv_smi,
                                "--query-gpu=gpu_name,memory.used,memory.total,utilization.gpu",
                                "--format=csv,noheader,nounits",
                            ],
                            capture_output=True,
                            text=True,
                            check=True,
                        )
                        for line in res.stdout.strip().split("\n"):
                            if line:
                                parts = [p.strip() for p in line.split(",")]
                                if len(parts) >= 4:
                                    gpus.append(
                                        {
                                            "name": parts[0],
                                            "used_mb": int(parts[1]),
                                            "total_mb": int(parts[2]),
                                            "util_percent": float(parts[3]),
                                            "type": "NVIDIA",
                                        }
                                    )
                    except Exception:
                        pass

                if platform.system() == "Windows":
                    try:
                        cmd = "Get-CimInstance Win32_VideoController | Select-Object Name, AdapterRAM | ConvertTo-Json"
                        res = subprocess.run(
                            ["powershell", "-NoProfile", "-Command", cmd],
                            capture_output=True,
                            text=True,
                            timeout=5,
                        )
                        if res.returncode == 0 and res.stdout.strip():
                            data = json.loads(res.stdout.strip())
                            if isinstance(data, dict):
                                data = [data]
                            for item in data:
                                name = item.get("Name")
                                if name:
                                    if (
                                        "Microsoft Basic Display Adapter" in name
                                        and len(data) > 1
                                    ):
                                        continue
                                    if any(
                                        g["name"].lower() in name.lower()
                                        or name.lower() in g["name"].lower()
                                        for g in gpus
                                    ):
                                        continue
                                    ram_bytes = item.get("AdapterRAM", 0)
                                    ram_mb = 0
                                    if isinstance(ram_bytes, int) and ram_bytes > 0:
                                        ram_mb = ram_bytes // (1024**2)
                                    gpus.append(
                                        {
                                            "name": name,
                                            "used_mb": None,
                                            "total_mb": ram_mb if ram_mb > 0 else None,
                                            "util_percent": None,
                                            "type": "Windows",
                                        }
                                    )
                    except Exception:
                        pass

                # Format printouts
                logger.info(
                    f"  {C.BOLD}Platform     :{C.RESET} {os_name} {os_release} ({os_arch})"
                )
                logger.info(f"  {C.BOLD}Python       :{C.RESET} v{py_ver}")
                logger.info(f"  {C.BOLD}System Uptime:{C.RESET} {uptime_str}")
                logger.info(
                    f"  {C.SLATE}──────────────────────────────────────────────────────────────────────{C.RESET}"
                )
                logger.info(
                    f"  {C.BOLD}CPU Load     :{C.RESET} [{cpu_bar}] {C.BOLD}{cpu:.1f}%{C.RESET}"
                )
                logger.info(
                    f"  {C.BOLD}Memory (RAM) :{C.RESET} [{mem_bar}] {C.BOLD}{mem.percent:.1f}%{C.RESET} ({mem_used_mb}MB used of {mem_total_mb}MB)"
                )
                logger.info(
                    f"  {C.BOLD}Storage (/)  :{C.RESET} [{disk_bar}] {C.BOLD}{disk.percent:.1f}%{C.RESET} ({disk_free_gb}GB free of {disk_total_gb}GB)"
                )

                if gpus:
                    logger.info(
                        f"  {C.SLATE}──────────────────────────────────────────────────────────────────────{C.RESET}"
                    )
                    for idx, gpu in enumerate(gpus, 1):
                        gpu_name = gpu["name"]
                        if gpu["util_percent"] is not None:
                            gpu_bar = make_bar(gpu["util_percent"])
                            vram_used = gpu["used_mb"]
                            vram_total = gpu["total_mb"]
                            logger.info(
                                f"  {C.BOLD}GPU #{idx} Load  :{C.RESET} [{gpu_bar}] {C.BOLD}{gpu['util_percent']:.1f}%{C.RESET} ({gpu_name})"
                            )
                            logger.info(
                                f"  {C.BOLD}GPU #{idx} VRAM  :{C.RESET} {vram_used}MB used of {vram_total}MB"
                            )
                        else:
                            vram_str = (
                                f" ({gpu['total_mb']}MB VRAM)"
                                if gpu["total_mb"]
                                else ""
                            )
                            logger.info(
                                f"  {C.BOLD}GPU #{idx} (Aux) :{C.RESET} {gpu_name}{vram_str}"
                            )

                logger.info(
                    f"  {C.SLATE}──────────────────────────────────────────────────────────────────────{C.RESET}"
                )
                logger.info(
                    f"  {C.BOLD}Agent Process:{C.RESET} PID={C.PURPLE}{pid}{C.RESET} | Memory={C.PURPLE}{proc_mem_mb}MB{C.RESET} | Uptime={C.PURPLE}{time.time() - proc.create_time():.1f}s{C.RESET}"
                )
            except Exception as e:
                print_error(f"Failed to gather system metrics: {e}")
            logger.info("")

        else:
            print_error(f"Unknown command: {base}. Type /help.")

    def run(self, task: Optional[str] = None):
        """run function."""
        banner(cfg=self.cfg)

        autonomy_cfg = self.cfg.get("autonomy", {})
        if autonomy_cfg.get("startup_provider_prompt", False) and not task:
            self.select_provider(force=False)

        # Connection check
        provider = self.cfg["agent"].get("provider", "ollama").lower()
        if provider == "ollama":
            models = self.agent.client.list_models()
            if not models:
                print_error("Ollama not reachable. Start with: `ollama serve`")
                print_info(f"Continuing with '{self.agent.client.model}' (may fail)")
            else:
                print_success(f"Ollama connected — {len(models)} model(s) available.")
                print_info(f"Active model: {C.BOLD}{self.agent.client.model}{C.RESET}")
        elif provider == "gemini":
            key_status = "[SET]" if self.agent.client.api_key else "NOT SET"
            print_success("Google Gemini provider connected.")
            print_info(f"API key: {key_status}")

        else:
            key_status = "[SET]" if self.agent.client.api_key else "NOT SET"
            print_success("Nvidia NIM provider connected.")
            print_info(f"API key: {key_status}")

        if autonomy_cfg.get("startup_model_prompt", False) and not task:
            # Non-forced by default so startup can remain quick for autopilot runs.
            self.select_model(force=False)

        print_success(
            f"Tools loaded: {len(self.agent.ops.registry)} ops available."
        )

        if task:
            logger.info(f"\n{C.BOLD}Executing autonomous task:{C.RESET} {task}\n")
            try:
                self.agent.run(task)
            except KeyboardInterrupt:
                logger.info(f"\n{C.YELLOW}Task interrupted.{C.RESET}")
            except Exception as e:
                print_error(f"Unexpected error: {e}")
                traceback.print_exc()
            return

        logger.info(
            f"\n{C.DIM}Type your task, or /help for commands. Ctrl+C or /exit to quit.{C.RESET}\n"
        )

        if readline:
            try:
                if hasattr(readline, "set_completer_delims"):
                    delims = readline.get_completer_delims()
                    if "/" in delims:
                        readline.set_completer_delims(delims.replace("/", ""))
                completer = CommandCompleter(self.COMMANDS.keys(), self)
                readline.set_completer(completer.complete)
                readline.parse_and_clid("tab: complete")
            except (RuntimeError, ImportError) as e:
                print_warning(f"Warning: Failed to configure autocompletion: {e}")

        while self.running:
            try:
                raw = input(f"{C.BOLD}AgenticOs{C.RESET} {C.CYAN}❯{C.RESET} ").strip()
            except KeyboardInterrupt:
                logger.info(f"\n{C.CYAN}Interrupted. Type /exit to quit.{C.RESET}")
                continue
            except EOFError:
                self.handle_command("/exit")
                break

            if not raw:
                continue

            if raw.startswith("/"):
                self.handle_command(raw)
            else:
                try:
                    self.agent.run(raw)
                except KeyboardInterrupt:
                    logger.info(f"\n{C.YELLOW}Task interrupted.{C.RESET}")
                except Exception as e:
                    print_error(f"Unexpected error: {e}")
                    traceback.print_exc()


def main(dry_run: bool = False):
    """main function."""
    if not dry_run and "--dry-run" in sys.argv:
        dry_run = True
    try:
        task_args = [arg for arg in sys.argv[1:] if not arg.startswith("-")]
        task = " ".join(task_args) if task_args else None
        CLI(dry_run=dry_run).run(task=task)
    except RuntimeError as e:
        logger.info(f"\n\033[91mError: {e}\033[0m")
        logger.info(
            "\033[33mAdd the missing key to your .env file and restart.\033[0m\n"
        )
        raise SystemExit(1)


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    main()
