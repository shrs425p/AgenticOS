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

from core.audit_logger import AuditLogger, infer_success
from core.context_engine import ContextEngine
from core.logger import get_logger
from core.memory_manager import initialize_memory_manager, log_task_completion
from core.model_clients import (
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
from core.runtime_config import BASE_DIR, DEFAULT_WORKSPACE, load_config
from core.runtime_ui import (
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
from core.session_memory_sqlite import SqliteSessionMemory
from core.task_tracker import TaskTracker
from core.tool_registry import ToolRegistry

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


class Agent:
    def __init__(self, cfg: dict, confirm_handler: Optional[Callable] = None):
        self.cfg = cfg
        self.confirm_handler = confirm_handler

        self._load_agent_settings()
        self._init_client()
        self._setup_workspace()
        self._init_audit_and_task_tracker()

        if self.autonomy_cfg.get("autopilot", False):
            self.confirm = True

        self._init_engine()
        self._init_hot_reload()

    def _load_agent_settings(self) -> None:
        self.heuristics = self.cfg.get("heuristics", {})
        self.performance = self.cfg.get("performance", {})
        self.enable_cov = self.cfg["agent"].get("enable_cov", True)
        self.cov_model = self.heuristics.get("cov_model")
        self.max_iter = self.cfg["agent"]["max_iterations"]
        self.verbose = self.cfg["agent"]["verbose_thinking"]
        self.confirm = self.cfg["agent"].get("auto_confirm", True)
        self.hot_reload_enabled = self.cfg["agent"].get("hot_reload", True)
        self.autonomy_cfg = self.cfg.get("autonomy", {})

    def _create_client(self, provider: str):
        client_name = PROVIDER_CLIENT_MAP.get(provider, "OllamaClient")
        client_cls = getattr(sys.modules[__name__], client_name)
        return client_cls(self.cfg)

    def _init_client(self) -> None:
        provider = self.cfg["agent"].get("provider", "ollama").lower()
        self.client = self._create_client(provider)

        fallback_providers = self.cfg["agent"].get("fallback_providers", []) or []
        if fallback_providers:
            fallback_clients = []
            for fb_provider in fallback_providers:
                fb_provider = fb_provider.strip().lower()
                if fb_provider != provider and fb_provider in PROVIDER_CLIENT_MAP:
                    try:
                        fallback_clients.append(self._create_client(fb_provider))
                    except RuntimeError as e:
                        print_warning(
                            f"Warning: Failed to initialize fallback client {fb_provider}: {e}"
                        )
            if fallback_clients:
                self.client = TieredClient(self.client, fallback_clients)

    def _setup_workspace(self) -> None:
        self.workspace = os.path.abspath(
            self.cfg["agent"].get("workspace", DEFAULT_WORKSPACE)
        )
        memory_cfg = dict(self.cfg.get("memory", {}))
        memory_cfg.setdefault("workspace", self.workspace)
        sqlite_cfg = dict(memory_cfg)
        db_path = sqlite_cfg.pop("sqlite_db_path", "") or ""
        if db_path:
            sqlite_cfg["db_path"] = db_path
        self.memory = SqliteSessionMemory(sqlite_cfg)

        self.tools = ToolRegistry(
            self.cfg, memory_backend=self.memory, confirm_handler=self.confirm_handler
        )

    def _init_audit_and_task_tracker(self) -> None:
        logging_cfg = self.cfg.get("logging", {}) or {}
        audit_enabled = bool(logging_cfg.get("audit_enabled", True))
        audit_dir = logging_cfg.get("audit_dir") or os.path.join(self.workspace, "logs")
        if not os.path.isabs(audit_dir):
            audit_dir = os.path.join(BASE_DIR, audit_dir)
        audit_fmt = (logging_cfg.get("audit_format") or "jsonl").lower().strip()
        self.audit = AuditLogger(
            audit_dir, enabled=audit_enabled, fmt=audit_fmt, cfg=self.cfg
        )

        self.session_id = getattr(
            self.memory,
            "session_id",
            datetime.now().strftime(
                self.heuristics.get("session_id_format", "%Y%m%d_%H%M%S")
            ),
        )
        try:
            self.audit.session_start(
                session_id=self.session_id,
                provider=self.client.provider,
                model=self.client.model,
                workspace=self.workspace,
            )
        except (IOError, OSError) as e:
            print_warning(f"Warning: Failed to log audit session: {e}")
            pass

        self.task_tracker = TaskTracker(
            self.workspace,
            session_id=self.session_id,
            cfg=self.cfg,
        )

    def _init_engine(self) -> None:
        self.context_engine = ContextEngine(self)
        mm = initialize_memory_manager(self.workspace, self.client, self.cfg)
        self.context_engine.set_memory_manager(mm)

        os.makedirs(self.workspace, exist_ok=True)
        file_templates = self.cfg.get("prompts", {}).get("file_templates", {})
        for init_file, default_content in [
            (
                "AGENTS.md",
                "# Agent Identity\n\nDefine your agent persona and rules here.\n",
            ),
            (
                "MEMORY.md",
                "# AgenticOs Long-Term Memory\n\nCurated knowledge, insights, and learned patterns from agent experiences.\n",
            ),
            (
                "USERINFO.md",
                "# User Profile\n\nStore user name, preferences, and personal info here.\n",
            ),
        ]:
            init_content = file_templates.get(init_file, default_content)
            init_path = os.path.join(self.workspace, init_file)
            if not os.path.exists(init_path):
                try:
                    with open(init_path, "w", encoding="utf-8") as f:
                        f.write(init_content)
                except (IOError, OSError) as e:
                    print_warning(
                        f"Warning: Failed to create initialization file {init_file}: {e}"
                    )

    def _init_hot_reload(self) -> None:
        self.mtimes: Dict[str, float] = (
            self._get_mtimes() if self.hot_reload_enabled else {}
        )
        self._last_reload_check = time.time()
        self._reload_throttle = float(self.heuristics.get("hot_reload_throttle", 2.0))
        self._cached_system = None

    def _reload_config(self) -> None:
        old_workspace = getattr(self, "workspace", None)
        self.cfg = load_config(force_reload=True)
        self._load_agent_settings()
        self._init_client()

        new_workspace = os.path.abspath(
            self.cfg["agent"].get("workspace", DEFAULT_WORKSPACE)
        )
        if new_workspace != old_workspace:
            self.workspace = new_workspace
            self._setup_workspace()
        else:
            # Reinitialize memory if memory config changed and workspace path is unchanged
            self._setup_workspace()

        self.task_tracker = TaskTracker(
            self.cfg["agent"].get("workspace", DEFAULT_WORKSPACE),
            session_id=self.session_id,
            cfg=self.cfg,
        )

    def _get_mtimes(self) -> Dict[str, float]:
        mtimes: Dict[str, float] = {}
        tracked_dirs = [
            os.path.join(BASE_DIR, d)
            for d in self.cfg.get("hot_reload", {}).get(
                "tracked_dirs", ["core", "tools", "scripts"]
            )
        ]
        if BASE_DIR not in tracked_dirs:
            tracked_dirs.append(BASE_DIR)

        blacklisted_dirs = {
            "venv",
            "node_modules",
            "workspace",
            "data",
            "mock_workspace",
        }
        try:
            for directory in tracked_dirs:
                if not os.path.isdir(directory):
                    continue
                for root, dirs, files in os.walk(directory):
                    dirs[:] = [
                        d
                        for d in dirs
                        if d != "__pycache__"
                        and not d.startswith(".")
                        and d not in blacklisted_dirs
                    ]
                    for name in files:
                        if not (name.endswith(".py") or name == "config.yaml"):
                            continue
                        abs_path = os.path.join(root, name)
                        rel_path = os.path.relpath(abs_path, BASE_DIR)
                        mtimes[rel_path] = os.path.getmtime(abs_path)
        except OSError:
            return mtimes
        return mtimes

    def check_reload(self):
        """check_reload function."""
        if not self.hot_reload_enabled:
            return

        now = time.time()
        if now - self._last_reload_check < self._reload_throttle:
            return
        self._last_reload_check = now

        new_mtimes = self._get_mtimes()
        changed_files = []
        for f, mt in new_mtimes.items():
            if f not in self.mtimes or mt > self.mtimes[f]:
                changed_files.append(f)

        if changed_files:
            self._cached_system = None  # Invalidate cache
            self._reload_everything(changed_files, new_mtimes)

    def _reload_everything(self, changed_files, new_mtimes=None):
        if isinstance(changed_files, str):
            changed_files = [changed_files]

        try:
            config_changed = "config.yaml" in changed_files
            py_changed = any(f.endswith(".py") for f in changed_files)

            if config_changed:
                logger.info(
                    f"{C.YELLOW}↻  Config changed: config.yaml. Refreshing settings...{C.RESET}"
                )
                self._reload_config()

            if py_changed:
                import importlib

                # If any tool-related file changed, force a reload of the registry and major mixins
                for f in changed_files:
                    if "tools" in f or "core/tool_registry" in f:
                        for mod in [
                            "tools.web_tools",
                            "core.tool_registry",
                            "tools.web.spotify",
                            "tools.web.browser",
                        ]:
                            if mod in sys.modules:
                                try:
                                    importlib.reload(sys.modules[mod])
                                except (ImportError, AttributeError) as e:
                                    print_warning(
                                        f"Warning: Failed to reload module {mod}: {e}"
                                    )

                # Standard reload for other changed modules
                for f in changed_files:
                    if f.endswith(".py"):
                        mod_name = os.path.splitext(f)[0].replace(os.sep, ".")
                        if mod_name in sys.modules:
                            logger.info(
                                f"{C.YELLOW}↻  File changed: {f}. Reloading module...{C.RESET}"
                            )
                            importlib.reload(sys.modules[mod_name])

            # Re-initialize tool registry
            import core.tool_registry

            importlib.reload(core.tool_registry)
            self.tools = core.tool_registry.ToolRegistry(
                self.cfg,
                memory_backend=self.memory,
                confirm_handler=self.confirm_handler,
            )
            self.mtimes = new_mtimes or self._get_mtimes()
            self._cached_system = None  # Ensure cache is cleared
            print_success("Environment reloaded successfully.")

        except Exception as e:
            print_error(
                f"Reload failed: An error occurred while hot-reloading changed modules: {e}\n{traceback.format_exc()}"
            )
            self.mtimes = new_mtimes or self._get_mtimes()

        # Add null check before calling build_system_prompt
        if self.context_engine is None:
            print_error("Context engine failed to initialize during reload")
            return ""
        return self.context_engine.build_system_prompt()

    def verify_action(
        self, tool_name: str, args: Dict, context: str
    ) -> Tuple[bool, str]:
        """
        Performs a 'mental simulation' to verify if the tool call is valid and necessary.
        """
        # Hard Check: Tool Existence
        if tool_name not in self.tools.registry:
            return (
                False,
                f"Tool '{tool_name}' is not in the registry. Check /tools for available capabilities.",
            )

        # Soft Check: Model Verification
        verification_cfg = self.cfg.get("prompts", {}).get("verification", {})
        prompt_tmpl = verification_cfg.get("prompt", "").strip()
        if not prompt_tmpl:
            prompt_tmpl = (
                "You are the Technical Verification Monitor for AgenticOs.\n"
                "Your ONLY job is to verify the technical validity and safety of the proposed action.\n\n"
                "TOOL: {tool_name}\n"
                "ARGS: {args}\n\n"
                "CONTEXT (Recent history):\n"
                "{context}\n\n"
                "STRICT VERIFICATION RULES:\n"
                "1. TECHNICAL VALIDITY: Are the arguments logically sound? (e.g. if reading a file, has it been identified/created?)\n"
                "2. ANTI-LOOP: Is the agent repeating the EXACT same command that just failed or yielded no new info?\n"
                "3. NO STRATEGY JUDGMENT: Do NOT reject an action because it is 'insufficient' to solve the whole task. "
                "Tasks are solved via MANY small, sequential steps. Sequential searches are VALID.\n"
                "4. TOOL EXISTENCE: Assume the tool '{tool_name}' is valid and registered. Do NOT reject based on tool name existence.\n\n"
                "REPLY FORMAT:\n"
                "If the action is technically valid, reply ONLY with 'OK'.\n"
                "If invalid, broken, or a loop, reply 'REJECT: [concise technical reason]'"
            )

        prompt = prompt_tmpl.format(tool_name=tool_name, args=args, context=context)

        try:
            # Use cov_model if specified, otherwise use active model
            original_model = self.client.model
            if self.cov_model:
                self.client.model = self.cov_model

            # Use a minimal message history for speed
            verification_msgs = [{"role": "user", "content": prompt}]
            system_msg = verification_cfg.get(
                "system", "You are a strict verification monitor."
            )
            response = self.client.chat(verification_msgs, system=system_msg)

            if self.cov_model:
                self.client.model = original_model

            response = response.strip()
            if response.upper() == "OK":
                return True, "OK"
            elif response.upper().startswith("REJECT:"):
                return False, response[7:].strip()
            else:
                # Ambiguous response, default to OK but log it
                return True, "OK"
        except Exception as e:
            return True, f"Verification skipped due to error: {e}"

    def _is_direct_response(self, user_input: str, response: str) -> bool:
        """Accept direct replies without forcing tool/action format.

        This is intentionally structural, not phrase-based: the model can finish
        if it produced answer-like text with no tool/control markers, or if it is
        asking a clarification question.
        """
        text = (response or "").strip()
        max_chars = int(self.heuristics.get("direct_response_max_chars", 6000))
        max_words = int(self.heuristics.get("direct_response_max_words", 900))
        if not text or len(text) > max_chars:
            return False
        upper = text.upper()
        control_markers = self.cfg.get("parser", {}).get(
            "keywords",
            [
                "OBJECTIVE:",
                "TASK:",
                "PLAN:",
                "CURRENT_STEP:",
                "STRATEGY:",
                "ACTION:",
                "OBSERVATION:",
            ],
        )
        if any(marker in upper for marker in control_markers):
            return False
        if has_final_answer(text):
            return True

        response_words = text.split()
        if len(response_words) > max_words:
            return False

        # Clarifying questions are legitimate terminal responses when no tool can
        # be chosen yet.
        if text.endswith("?"):
            return True

        return True

    def run(self, user_input: str):
        """run function."""
        run_started_ts = time.time()
        original_user_input = user_input
        if self.memory.turn_count == 0:
            try:
                sys_info = self.tools.term.system_info()
                user_input = f"[System Context: {sys_info.replace(chr(10), ' ')}]\n\n{user_input}"
            except RuntimeError as e:
                print_warning(f"Warning: Failed to gather system info: {e}")

            # Auto-load preferences into context
            try:
                mem = getattr(self, "memory", None)
                if mem and hasattr(mem, "list_preferences"):
                    prefs = mem.list_preferences()
                    if isinstance(prefs, dict) and prefs:
                        items = []
                        max_p_chars = self.performance.get("max_pref_chars", 80)
                        max_p_items = self.performance.get("max_pref_items", 20)
                        for k in sorted(prefs.keys()):
                            v = str(prefs[k])
                            if len(v) > max_p_chars:
                                v = v[:max_p_chars] + "..."
                            items.append(f"{k}={v}")
                        if items:
                            user_input = (
                                "[Preferences: "
                                + ", ".join(items[:max_p_items])
                                + "]\n\n"
                                + user_input
                            )
            except Exception as e:
                print_error(
                    f"Failed to load preferences from memory: {e}. Check if the database connection or table schema is correct."
                )

        if self.autonomy_cfg.get("task_tracking", True):
            should_start_new = True
            curr_task = self.task_tracker.current
            if curr_task and curr_task.get("status") == "running":
                resumption_cmds = self.heuristics.get(
                    "resumption_cmds", ["continue", "next"]
                )
                min_chars = self.heuristics.get("new_task_min_chars", 10)
                if (
                    original_user_input.lower().strip() in resumption_cmds
                    or len(original_user_input) < min_chars
                ):
                    should_start_new = False

            if should_start_new:
                self.task_tracker.start(
                    goal=original_user_input,
                    provider=self.client.provider,
                    model=self.client.model,
                )
                curr_task = self.task_tracker.current
                if hasattr(self.memory, "start_task") and curr_task:
                    try:
                        self.memory.start_task(
                            curr_task["task_id"], original_user_input
                        )
                    except (IOError, OSError, ValueError) as e:
                        print_warning(f"Warning: Failed to start task in memory: {e}")

        self.memory.add("user", user_input)
        messages = self.memory.get_messages()

        # Phase 3: Context Compaction — compress long histories before they hit token limits
        max_msgs = int(self.performance.get("max_context_messages", 40))
        messages = self.context_engine.compact_history(messages, max_messages=max_msgs)

        last_response = None
        repetition_count = 0
        last_action_signature = None
        repeated_action_count = 0
        no_action_count = 0
        minimal_clarifications = self.autonomy_cfg.get("minimal_clarifications", True)

        limitless = self.max_iter <= 0
        iteration = 0
        while True:
            iteration += 1
            if not limitless and iteration > self.max_iter:
                break
            self.check_reload()

            # Active Recall & Commitments (Phase 2 Proactive Architecture)
            recall = self.context_engine.get_active_recall(original_user_input)
            commitments = self.context_engine.get_commitments()

            system = self.context_engine.build_system_prompt(recall, commitments)

            # Detect repetitive loops
            if repetition_count >= 2:
                repetition_count = 0
                reminder = (
                    self.cfg.get("prompts", {})
                    .get("nudges", {})
                    .get(
                        "repetition",
                        "You're repeating the same approach. Try a COMPLETELY DIFFERENT strategy.",
                    )
                )
                messages.append({"role": "user", "content": reminder})
                logger.info(
                    f"{C.YELLOW}▲  Repetition detected. Suggesting alternative approach.{C.RESET}"
                )

            # Warn if iterations getting high (skip if warning_threshold is <= 0)
            warning_threshold = self.heuristics.get("iteration_warning_threshold", 20)
            if (
                warning_threshold > 0
                and iteration > warning_threshold
                and iteration % 10 == 0
            ):
                logger.info(
                    f"{C.YELLOW}▲  High iteration count ({iteration}). Consider FINAL ANSWER.{C.RESET}"
                )

            pulse_line(60)
            iter_label = (
                f"{iteration}/∞" if limitless else f"{iteration}/{self.max_iter}"
            )
            logger.info(f"{C.DIM}Iteration {iter_label}{C.RESET}")

            try:
                response = self.client.chat(messages, system=system)

                # DE-HALLUCINATION FILTER
                response = re.sub(r"(?i)Iteration \d+/\d+", "", response)
                response = re.sub(r"(?i)AgenticOs\s*❯", "", response)
                response = response.strip()

                # SANITY FILTER: Detect dot-loops
                max_dots = self.heuristics.get("max_dots_in_response", 50)
                if "..." in response and response.count(".") > max_dots:
                    response = response.split("...")[0] + "... [TRUNCATED LOOP]"
                if "\n\n\n\n\n" in response:
                    response = (
                        response.split("\n\n\n\n\n")[0] + "\n [TRUNCATED WHITESPACE]"
                    )

                if self.autonomy_cfg.get("active_planning", True):
                    self.task_tracker.update_from_response(response, iteration)

                # Update repetition tracking
                if last_response and response.strip() == last_response.strip():
                    repetition_count += 1
                else:
                    repetition_count = 0
                last_response = response
            except Exception as e:
                print_error(f"Model error with '{self.client.model}': {e}")

                # Auto-fallback: Switch to a random model and retry
                models = self.client.list_models()
                if len(models) > 1:
                    # Filter out current model
                    others = [m for m in models if m != self.client.model]
                    new_model = random.choice(others)
                    logger.info(
                        f"{C.YELLOW}▲  Attempting auto-fallback to: {new_model}{C.RESET}"
                    )
                    self.client.model = new_model
                    # Consumes one iteration to retry with the new model
                    continue
                else:
                    print_error("No alternative models available for fallback.")
                    return

            if not response.strip():
                # Treat empty output as a retryable transient (often reasoning-only streams).
                print_warning(
                    "Empty response from model. Retrying with a stricter instruction..."
                )
                messages.append(
                    {
                        "role": "user",
                        "content": self.cfg.get("prompts", {})
                        .get("nudges", {})
                        .get(
                            "empty_response",
                            "Your last message was empty. Respond NOW with one of the required formats and include ACTION if any tool is needed.",
                        ),
                    }
                )
                self.memory.add("user", messages[-1]["content"])
                no_action_count += 1
                # If we keep getting empties, attempt a model fallback (if available).
                if no_action_count >= 3:
                    try:
                        models = self.client.list_models()
                        others = [m for m in models if m != self.client.model]
                        if others:
                            new_model = random.choice(others)
                            logger.info(
                                f"{C.YELLOW}▲  Empty-loop fallback to: {new_model}{C.RESET}"
                            )
                            self.client.model = new_model
                            no_action_count = 0
                    except (RuntimeError, ValueError) as e:
                        print_warning(f"Warning: Failed to perform model fallback: {e}")
                continue

            r_upper = response.strip().upper()
            direct_response = self._is_direct_response(original_user_input, response)
            # More flexible format checking - allow direct answers, task format, or objective format
            valid_formats = (
                r_upper.startswith("OBJECTIVE:")
                or r_upper.startswith("TASK:")
                or "FINAL ANSWER:" in r_upper
                or "ACTION" in r_upper
                or direct_response
            )
            if not valid_formats:
                if "FINAL ANSWER:" not in r_upper:
                    print_warning("Model output unclear. Reminding about format...")
                    messages.append({"role": "assistant", "content": response})
                    obs = (
                        self.cfg.get("prompts", {})
                        .get("nudges", {})
                        .get(
                            "format_error",
                            "Please respond with one of these: 1) FINAL ANSWER: ... 2) OBJECTIVE/PLAN/CURRENT_STEP/ACTION 3) TASK/CONTEXT/STRATEGY/ACTION",
                        )
                    )
                    # In autopilot/minimal-clarifications mode, keep nudges short and action-oriented.
                    nudge = obs if minimal_clarifications else f"Clarification: {obs}"
                    messages.append({"role": "user", "content": nudge})
                    self.memory.add("assistant", response)
                    self.memory.add("user", nudge)
                    continue

            actions = parse_actions(response)

            if not actions and "ACTION:" in response.upper():
                messages.append({"role": "assistant", "content": response})
                self.memory.add("assistant", response)
                nudge = "OBSERVATION: Tool parsing failed. You attempted a tool call under ACTION:, but the JSON was malformed or contained unescaped control characters (such as literal newlines). Please retry your action, escaping all newlines as '\\n' in JSON string values. Output exactly ONE action per turn and wait for the real observation."
                messages.append({"role": "user", "content": nudge})
                self.memory.add("user", nudge)
                continue

            if actions:
                no_action_count = 0

                # Prevent wasting turns on the same action sequence repeatedly.
                current_signature = "||".join([f"{t}|{args}" for t, args in actions])
                if current_signature == last_action_signature:
                    repeated_action_count += 1
                else:
                    last_action_signature = current_signature
                    repeated_action_count = 0

                if repeated_action_count >= 2:
                    obs = "Blocked repeated action sequence with identical arguments. Try a different approach."
                    print_warning("Prevented repeated identical action sequence.")
                    print_observation(obs)
                    messages.append({"role": "assistant", "content": response})
                    messages.append({"role": "user", "content": f"OBSERVATION: {obs}"})
                    self.memory.add("assistant", response)
                    self.memory.add("user", f"OBSERVATION: {obs}")
                    continue

                observations = []
                for tool_name, args in actions:
                    symbol = self.tools.get_symbol(tool_name)
                    print_action(tool_name, args, symbol)

                    # Chain-of-Verification (Mental Simulation)
                    if self.enable_cov:
                        verification_context = "\n".join(
                            [
                                f"{m['role'].upper()}: {m['content'][:500]}"
                                for m in messages[-3:]
                            ]
                        )
                        verification_context += f"\nASSISTANT: {response[:500]}"
                        verified, reason = self.verify_action(
                            tool_name, args, verification_context
                        )
                        if not verified:
                            obs = f"Mental Verification Failed: {reason}"
                            print_warning(obs)
                            observations.append(obs)
                            continue

                    if self.autonomy_cfg.get("task_tracking", True):
                        self.task_tracker.record_action(tool_name, args)

                    # Optional confirmation for destructive actions
                    if (
                        self.cfg.get("rules", {}).get("require_confirm_destructive")
                        and not self.confirm
                    ):
                        destructive = set(
                            self.cfg.get("policy", {}).get(
                                "destructive_tools",
                                [
                                    "delete_file",
                                    "delete_dir",
                                    "kill_process",
                                    "run_command",
                                    "run_script",
                                ],
                            )
                        )
                        if tool_name in destructive:
                            try:
                                ans = (
                                    input(
                                        f"\n{C.RED}▲  Confirm destructive '{tool_name}'? [y/N]: {C.RESET}"
                                    )
                                    .strip()
                                    .lower()
                                )
                                if ans != "y":
                                    observations.append(
                                        f"Action '{tool_name}' cancelled by user."
                                    )
                                    continue
                            except (KeyboardInterrupt, EOFError):
                                print_info("\nCancelled.")
                                return

                    import time as _time

                    started = _time.time()
                    obs = self.tools.call(tool_name, args)
                    ended = _time.time()
                    observations.append(str(obs or "Done."))

                    ok = False
                    obs_text = ""

                    # Audit log tool call (no chat content).
                    try:
                        import json as _json

                        obs_text = str(obs or "")
                        validation = ""
                        for line in obs_text.splitlines():
                            if line.strip().upper().startswith("VALIDATION:"):
                                validation = line.strip()
                                break
                        ok = infer_success(obs_text)
                        if validation and (
                            "missing" in validation.lower()
                            or "still exists" in validation.lower()
                        ):
                            ok = False
                        self.audit.tool_call(
                            session_id=self.session_id,
                            tool_name=tool_name,
                            tool_args=(
                                _json.dumps(args, ensure_ascii=False)
                                if isinstance(args, (dict, list))
                                else str(args)
                            ),
                            started_ts=started,
                            ended_ts=ended,
                            success=ok,
                            validation=validation,
                            observation_preview=obs_text,
                        )
                    except Exception as exc:
                        try:
                            self.audit.error(
                                self.session_id, "audit.tool_call", str(exc)
                            )
                        except (IOError, OSError) as e:
                            print_warning(f"Warning: Failed to log audit error: {e}")

                    # Log security validation events to audit trail and logger.
                    try:
                        if not ok and "blocked by safety rules" in obs_text.lower():
                            self.audit.error(
                                self.session_id,
                                "security_validation",
                                f"Security warning: {obs_text}",
                            )
                            logger.warning(
                                "SECURITY WARNING: Command execution blocked by safety rules: %s",
                                (
                                    _json.dumps(args, ensure_ascii=False)
                                    if isinstance(args, (dict, list))
                                    else str(args)
                                ),
                            )
                    except Exception:
                        pass

                    # Persist tool events + artifacts for SQLite memory backend.
                    if hasattr(self.memory, "record_tool_event"):
                        try:
                            import json as _json

                            self.memory.record_tool_event(
                                tool_name=tool_name,
                                tool_args=(
                                    _json.dumps(args, ensure_ascii=False)
                                    if isinstance(args, (dict, list))
                                    else str(args)
                                ),
                                observation=str(obs),
                            )
                        except (IOError, OSError, ValueError) as e:
                            print_warning(f"Warning: Failed to record tool event: {e}")

                    if hasattr(self.memory, "record_artifact"):
                        try:
                            self._record_artifacts_from_tool(tool_name, args)
                        except (IOError, OSError, ValueError) as e:
                            print_warning(f"Warning: Failed to record artifact: {e}")

                    curr_task = self.task_tracker.current
                    if hasattr(self.memory, "update_task") and curr_task:
                        try:
                            self.memory.update_task(curr_task["task_id"])
                        except (IOError, OSError, ValueError) as e:
                            print_warning(
                                f"Warning: Failed to update task in memory: {e}"
                            )
                    if self.autonomy_cfg.get("task_tracking", True):
                        self.task_tracker.record_observation(obs)

                # Combine all observations
                combined_obs = "\n---\n".join(observations)

                # Nudge if the model tried to batch actions (which we now truncate in parse_actions)
                if response.count("ACTION:") > 1:
                    batch_hint = "\n\nHINT: You attempted to call multiple tools. Only the first tool was executed. Please wait for the observation before calling the next tool. Call exactly ONE tool per turn."
                    combined_obs += batch_hint

                print_observation(combined_obs)

                # Limit observation length
                try:
                    max_obs_chars = int(
                        self.cfg.get("agent", {}).get(
                            "max_observation_chars",
                            self.heuristics.get("max_observation_chars", 12000),
                        )
                    )
                except ValueError as e:
                    print_warning(f"Warning: Invalid max_observation_chars config: {e}")
                    max_obs_chars = 12000

                if max_obs_chars and len(combined_obs) > max_obs_chars:
                    head_n = int(max_obs_chars * 0.7)
                    tail_n = max_obs_chars - head_n
                    combined_obs = (
                        combined_obs[:head_n]
                        + "\n... [TRUNCATED] ...\n"
                        + (combined_obs[-tail_n:] if tail_n > 0 else "")
                    )

                messages.append({"role": "assistant", "content": response})
                messages.append(
                    {"role": "user", "content": f"OBSERVATION: {combined_obs}"}
                )
                self.memory.add("assistant", response)
                self.memory.add("user", f"OBSERVATION: {combined_obs}")
                continue

            if direct_response and not has_final_answer(response):
                response = f"FINAL ANSWER: {response}"

            if has_final_answer(response):
                # ── Artifact Persistence Guardrail ──────────────────────────────────
                # If the agent mentions saving/writing/creating but hasn't called a tool to do so recently, nudge it.
                resp_lower = response.lower()
                mentions_save = any(
                    kw in resp_lower
                    for kw in [
                        "save",
                        "write",
                        "create",
                        "update",
                        "persist",
                        "report",
                        "analysis",
                        "content",
                    ]
                )

                if mentions_save:
                    # Look back at recent actions to see if any persistence tool was used.
                    recent_actions = []
                    # Check current response first (sometimes they include both ACTION and FINAL ANSWER, which is discouraged)
                    current_actions = parse_actions(response)
                    recent_actions.extend([t for t, _ in current_actions])

                    # Check recent history
                    for m in reversed(messages[-4:]):
                        if m["role"] == "assistant":
                            prev_actions = parse_actions(m["content"])
                            recent_actions.extend([t for t, _ in prev_actions])

                    persistence_tools = {
                        "write_file",
                        "append_file",
                        "create_plugin",
                        "write_json",
                        "write_csv",
                        "save_to_canvas",
                    }
                    persisted = any(t in recent_actions for t in persistence_tools)

                    if not persisted:
                        # Disabled heuristic: Was forcing write_file for long responses, but wastes API quota.
                        pass

                logger.info(
                    f"\n{C.EMERALD}  ── Final Answer ────────────────────────────────────────{C.RESET}"
                )

                final_ans = ""
                idx = response.upper().find("FINAL ANSWER:")
                if idx != -1:
                    final_ans = response[idx + 13 :].strip()
                    if final_ans.startswith("**"):
                        final_ans = final_ans[2:].strip()

                # Prevent saving an obvious system-prompt dump as final answer.
                if final_ans:
                    low_final = final_ans.lower()
                    prompt_dump_score = sum(
                        marker in low_final
                        for marker in (
                            "available_tools",
                            "workspace_root",
                            "thinking_canvas",
                            "active_task_memory",
                            "### ",
                            "-------------------------------------------",
                        )
                    )
                    if prompt_dump_score >= 2:
                        print_error(
                            "Model echoed system prompt instead of providing a final answer. Ignoring and continuing."
                        )
                        # Add a reminder to the conversation
                        messages.append(
                            {
                                "role": "user",
                                "content": "Please provide a genuine final answer to the task, not the system prompt. Focus on the user's request.",
                            }
                        )
                        self.memory.add(
                            "user",
                            "Please provide a genuine final answer to the task, not the system prompt. Focus on the user's request.",
                        )
                        continue

                if final_ans:
                    typewriter_print(f"{C.WHITE}{final_ans}{C.RESET}")
                    # Show task timing + token counts (best-effort estimates).
                    try:
                        elapsed_s = max(0.0, time.time() - run_started_ts)

                        def _est_tokens(s: str) -> int:
                            # Rough heuristic: ~4 chars per token for English-like text.
                            s = s or ""
                            return max(1, int(len(s) / 4))

                        try:
                            convo = (
                                system
                                + "\n"
                                + "\n".join((m.get("content") or "") for m in messages)
                            )
                        except (RuntimeError, ValueError) as e:
                            print_warning(
                                f"Warning: Failed to build conversation for token estimation: {e}"
                            )
                            convo = (system or "") + "\n" + (original_user_input or "")
                        down = _est_tokens(convo)
                        up = _est_tokens(response or "")
                        print_info(
                            f"Time: {elapsed_s:.1f}s | Tokens (est) down={down} up={up}"
                        )
                    except RuntimeError as e:
                        print_warning(
                            f"Warning: Failed to compute token estimates: {e}"
                        )

                    # Artifact-first workflow: persist a per-session result artifact.
                    try:
                        ws = self.cfg["agent"].get("workspace", DEFAULT_WORKSPACE)
                        if not os.path.isabs(ws):
                            ws = os.path.join(BASE_DIR, ws)
                        session_report_dir = os.path.join(
                            ws, "reports", str(self.session_id)
                        )
                        os.makedirs(session_report_dir, exist_ok=True)

                        report_cfg = self.cfg.get("prompts", {}).get(
                            "session_report", {}
                        )
                        file_name = report_cfg.get("file_name", "result.md")
                        out_path = os.path.join(session_report_dir, file_name)
                        is_new = not os.path.exists(out_path)

                        with open(out_path, "a", encoding="utf-8") as handle:
                            if is_new:
                                handle.write(
                                    report_cfg.get("header", "# Session Report\n\n")
                                )
                                handle.write(
                                    report_cfg.get(
                                        "metadata_header", "## Session Metadata\n\n"
                                    )
                                )
                                handle.write("| Field | Value |\n|-------|-------|\n")

                                row_tmpl = report_cfg.get(
                                    "metadata_table_row", "| **{key}** | `{value}` |\n"
                                )
                                handle.write(
                                    row_tmpl.format(
                                        key="Session ID", value=self.session_id
                                    )
                                )
                                handle.write(
                                    row_tmpl.format(
                                        key="Provider", value=self.client.provider
                                    )
                                )
                                handle.write(
                                    row_tmpl.format(
                                        key="Model", value=self.client.model
                                    )
                                )
                                handle.write(
                                    row_tmpl.format(
                                        key="Started",
                                        value=datetime.now().strftime(
                                            "%Y-%m-%d %H:%M:%S"
                                        ),
                                    )
                                )
                                handle.write("\n")

                            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            goal = "Task"
                            if (
                                self.task_tracker.current
                                and self.task_tracker.current.get("goal")
                            ):
                                goal = self.task_tracker.current.get("goal")

                            entry_tmpl = report_cfg.get(
                                "task_entry", "## COMPLETED [{ts}] {goal}\n\n"
                            )
                            handle.write(entry_tmpl.format(ts=ts, goal=goal))
                            handle.write(final_ans.strip() + "\n\n")
                            handle.write(report_cfg.get("footer", "---\n\n"))

                        try:
                            self.memory.record_artifact(
                                out_path, action="final_answer", kind="report"
                            )
                        except (IOError, OSError, ValueError) as e:
                            print_warning(
                                f"Warning: Failed to record result artifact: {e}"
                            )
                    except (IOError, OSError) as e:
                        print_warning(f"Warning: Failed to write session report: {e}")

                # Send notification per rule #9
                try:
                    msg = (
                        self.cfg.get("prompts", {})
                        .get("notifications", {})
                        .get("task_completed", "Task completed successfully.")
                    )
                    self.tools.ui.send_notification("AgenticOs", msg)
                except RuntimeError as e:
                    print_warning(f"Warning: Failed to send notification: {e}")

                self.memory.add("assistant", response)
                if self.autonomy_cfg.get("task_tracking", True):
                    self.task_tracker.complete(final_ans or response)

                # OpenClaw-inspired memory auto-compaction
                try:
                    goal = "Task"
                    curr_task = self.task_tracker.current
                    if curr_task and curr_task.get("goal"):
                        goal = curr_task.get("goal")

                    # Extract tools used from tracking
                    tools_used = []
                    if curr_task and curr_task.get("actions_taken"):
                        tools_used = [
                            a.get("tool")
                            for a in curr_task.get("actions_taken", [])
                            if a.get("tool")
                        ]

                    duration_s = max(0.0, time.time() - run_started_ts)
                    tracker_task_id = curr_task.get("task_id") if curr_task else None
                    log_task_completion(
                        goal=goal,
                        final_answer=final_ans or response,
                        tools_used=list(set(tools_used)),
                        success=True,
                        duration=duration_s,
                        task_id=tracker_task_id,
                    )
                except Exception as e:
                    print_error(
                        f"Failed to consolidate memory during experience logging: {e}"
                    )

                curr_task = self.task_tracker.current
                if hasattr(self.memory, "set_outcome"):
                    try:
                        next_steps = ""
                        if curr_task and curr_task.get("plan"):
                            next_steps = "\n".join(curr_task.get("plan", [])[-3:])
                        self.memory.set_outcome(
                            final_answer=final_ans or response, next_steps=next_steps
                        )
                    except ValueError as e:
                        print_warning(f"Warning: Failed to set outcome in memory: {e}")
                if hasattr(self.memory, "set_summary") and self.cfg.get(
                    "memory", {}
                ).get("auto_summarize", True):
                    try:
                        rpt = self.cfg.get("prompts", {}).get("reporting", {})
                        g_label = rpt.get("goal_label", "Goal:")
                        r_label = rpt.get("result_label", "Result:")
                        summary = f"{g_label} {original_user_input.strip()}\n{r_label} {(final_ans or '').strip()}"
                        self.memory.set_summary(summary.strip())
                    except ValueError as e:
                        print_warning(f"Warning: Failed to set summary in memory: {e}")
                curr_task = self.task_tracker.current
                if hasattr(self.memory, "complete_task") and curr_task:
                    try:
                        next_steps = ""
                        if curr_task.get("plan"):
                            next_steps = "\n".join(curr_task.get("plan", [])[-3:])
                        rpt = self.cfg.get("prompts", {}).get("reporting", {})
                        g_label = rpt.get("goal_label", "Goal:")
                        self.memory.complete_task(
                            curr_task["task_id"],
                            final_answer=final_ans or response,
                            next_steps=next_steps,
                            summary=f"{g_label} {original_user_input.strip()}",
                        )
                    except ValueError as e:
                        print_warning(
                            f"Warning: Failed to complete task in memory: {e}"
                        )
                return

            else:
                # Non-action intermediate response: keep going, but nudge toward a concrete next step.
                messages.append({"role": "assistant", "content": response})
                self.memory.add("assistant", response)
                no_action_count += 1
                if no_action_count >= 2 and self.autonomy_cfg.get(
                    "active_planning", True
                ):
                    no_action_count = 0
                    stall_obs = (
                        self.cfg.get("prompts", {})
                        .get("nudges", {})
                        .get(
                            "stall_detected",
                            (
                                "Stall detected: produce an ACTION (tool call) or FINAL ANSWER. "
                                "Update PLAN and CURRENT_STEP, then choose a concrete next action."
                            ),
                        )
                    )
                    print_warning("Stall detected. Requesting replan.")
                    if self.autonomy_cfg.get("task_tracking", True):
                        self.task_tracker.note_stall(stall_obs)
                    messages.append({"role": "user", "content": stall_obs})
                    self.memory.add("user", stall_obs)
                continue

        rpt = self.cfg.get("prompts", {}).get("reporting", {})
        max_iter_tmpl = rpt.get(
            "max_iter_reached",
            "Reached max iterations ({max_iter}) without a final answer.",
        )
        fail_msg = max_iter_tmpl.format(max_iter=self.max_iter)

        if self.autonomy_cfg.get("task_tracking", True):
            self.task_tracker.fail(fail_msg)
            # Log failed task completion
            tools_used = []
            goal = "Task"
            curr_task = self.task_tracker.current
            if curr_task:
                tools_used = [
                    a.get("tool")
                    for a in curr_task.get("actions_taken", [])
                    if a.get("tool")
                ]
                goal = curr_task.get("goal", goal)
            duration_s = max(0.0, time.time() - run_started_ts)
            tracker_task_id = curr_task.get("task_id") if curr_task else None
            try:
                log_task_completion(
                    goal=goal,
                    final_answer=fail_msg,
                    tools_used=list(set(tools_used)),
                    success=False,
                    duration=duration_s,
                    task_id=tracker_task_id,
                )
            except Exception as e:
                print_warning(f"Warning: Failed to log task history: {e}")

        print_error(fail_msg)
        try:
            self.audit.session_end(self.session_id, status="max_iterations")
        except (IOError, OSError) as e:
            print_warning(f"Warning: Failed to log audit session end: {e}")
        if hasattr(self.memory, "set_outcome"):
            try:
                self.memory.set_outcome(final_answer="", next_steps="")
            except ValueError as e:
                print_warning(f"Warning: Failed to set outcome on max iterations: {e}")

    def _record_artifacts_from_tool(self, tool_name: str, args):
        """Best-effort artifact capture for SQLite memory backend.

        Records touched paths for common filesystem tools.
        """
        if not hasattr(self.memory, "record_artifact"):
            return

        action = tool_name
        path_keys = ("path", "src", "dst", "output_path", "dest", "dest_path")
        values = []
        if isinstance(args, dict):
            for k in path_keys:
                v = args.get(k)
                if isinstance(v, str) and v.strip():
                    values.append(v.strip())
        elif isinstance(args, list):
            # Pipe format: infer first arg is usually a path for file tools.
            for a in args[:3]:
                if isinstance(a, str) and (
                    ":\\" in a
                    or a.startswith(".")
                    or a.startswith("/")
                    or a.endswith(
                        (".py", ".txt", ".md", ".json", ".yaml", ".yml", ".url")
                    )
                ):
                    values.append(a.strip())

        for v in values:
            self.memory.record_artifact(v, action=action, kind="path")


# ── CommandCompleter ──────────────────────────────────────────────────────────
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
        "/tools": "List all available tools",
        "/tool_report": "Write a markdown tool report into workspace (tool_report.md)",
        "/doctor": "Run quick health checks (config, memory db, logs, provider)",
        "/tools_md": "Write docs/tools_reference.md (tool name + description)",
        "/memory": "Show session memory summary",
        "/clear": "Clear session memory",
        "/reload": "Manually reload tools",
        "/config": "Open configuration folder in file explorer",
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
        self.cfg = load_config()
        self.agent = Agent(self.cfg, confirm_handler=self.handle_security_confirmation)
        self.running = True
        if dry_run:
            self.agent.tools.shadow_mode = True
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
            f"{C.SLATE}(You can allow this once, or modify config.yaml to change security rules){C.RESET}"
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

        elif base == "/tools":
            logger.info(
                f"\n{C.CYAN}{C.BOLD}Available Tools ({len(self.agent.tools.registry)}):{C.RESET}"
            )
            for name, info in self.agent.tools.registry.items():
                logger.info(
                    f"  {C.YELLOW}{name:<25}{C.RESET} {C.DIM}{info['desc']}{C.RESET}"
                )

        elif base == "/tool_report":
            # Authoritative: read directly from the registry, not from the truncated prompt.
            tools = sorted(self.agent.tools.registry.keys())
            lines = [
                "# Tool Report",
                "",
                f"**Total tools:** {len(tools)}",
                "",
            ]
            lines += [f"{i}. {name}" for i, name in enumerate(tools, 1)]
            lines.append("")
            out = self.agent.tools.fm.write_file("tool_report.md", "\n".join(lines))
            print_success(out)
            print_info(
                f"Wrote: {C.BOLD}{self.cfg['agent'].get('workspace', DEFAULT_WORKSPACE)}\\tool_report.md{C.RESET}"
            )

        elif base == "/tools_md":
            try:
                tools = sorted(
                    self.agent.tools.registry.items(), key=lambda kv: kv[0].lower()
                )
                out_dir = os.path.join(BASE_DIR, "docs")
                os.makedirs(out_dir, exist_ok=True)
                out_path = os.path.join(out_dir, "tools_reference.md")

                lines = []
                lines.append("# Tools Reference")
                lines.append("")
                lines.append(
                    f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
                lines.append(f"Total tools: {len(tools)}")
                lines.append("")
                lines.append("| Tool | Description |")
                lines.append("| --- | --- |")
                for name, info in tools:
                    desc = str((info or {}).get("desc", "")).strip().replace("\n", " ")
                    desc = desc.replace("|", "\\|")
                    lines.append(f"| `{name}` | {desc} |")
                lines.append("")

                with open(out_path, "w", encoding="utf-8") as handle:
                    handle.write("\n".join(lines))
                print_success(f"Wrote: {out_path}")
            except Exception as e:
                print_error(f"Failed to write tools_reference.md: {e}")

        elif base == "/doctor":
            logger.info(f"\n{C.CYAN}{C.BOLD}Doctor Checks:{C.RESET}")
            # 1) Config parse already succeeded if we got here.
            print_success("config.yaml: OK (parsed)")
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
            self.agent.tools.shadow_mode = not self.agent.tools.shadow_mode
            status = (
                f"{C.GREEN}ON{C.RESET}"
                if self.agent.tools.shadow_mode
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

        elif base == "/config":
            config_dir = os.path.join(BASE_DIR, "config")
            logger.info(f"\n{C.CYAN}Opening config folder: {config_dir}{C.RESET}")
            if not os.path.exists(config_dir):
                print_error(f"Config directory does not exist: {config_dir}")
            else:
                try:
                    if sys.platform == "win32":
                        os.startfile(config_dir)  # noqa: S606
                    elif sys.platform == "darwin":
                        subprocess.Popen(["open", config_dir])  # nosec B605
                    else:
                        subprocess.Popen(["xdg-open", config_dir])  # nosec B605
                    print_success("Config folder opened successfully.")
                except Exception as e:
                    print_error(f"Failed to open config folder: {e}")

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
            version_str = "2.1.2"
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
            logger.info(f"  Tools    : {len(self.agent.tools.registry)}")
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
            guard = getattr(getattr(self.agent, "tools", None), "guard", None)
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
            f"Tools loaded: {len(self.agent.tools.registry)} tools available."
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
                readline.parse_and_bind("tab: complete")
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
