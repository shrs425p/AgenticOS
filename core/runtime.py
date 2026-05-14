"""AgenticOs runtime orchestration."""

import os
import random
import sys
import time
import traceback
from datetime import datetime

try:
    import readline
except ImportError:
    try:
        from pyreadline3 import Readline as _Readline

        readline = _Readline()
    except ImportError:
        readline = None

import yaml
import requests
import re
from typing import Dict, Optional, Callable

import core.session_memory as memory
from core.session_memory_sqlite import SqliteSessionMemory
from core.audit_logger import AuditLogger, infer_success
from core.model_clients import GeminiClient, NvidiaClient, OllamaClient, GroqClient, OpenAIClient, OpenRouterClient, GithubClient, DeepseekClient
from core.runtime_config import BASE_DIR, DEFAULT_WORKSPACE, load_config
from core.task_tracker import TaskTracker
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
from core.tool_registry import ToolRegistry


class Agent:
    def __init__(self, cfg: dict, confirm_handler: Optional[Callable] = None):
        self.cfg = cfg
        self.confirm_handler = confirm_handler
        provider = cfg["agent"].get("provider", "ollama").lower()
        if provider == "nvidia":
            self.client = NvidiaClient(cfg)
        elif provider == "gemini":
            self.client = GeminiClient(cfg)
        elif provider == "groq":
            self.client = GroqClient(cfg)
        elif provider == "openai":
            self.client = OpenAIClient(cfg)
        elif provider == "openrouter":
            self.client = OpenRouterClient(cfg)
        elif provider == "github":
            self.client = GithubClient(cfg)
        elif provider == "deepseek":
            self.client = DeepseekClient(cfg)
        else:
            self.client = OllamaClient(cfg)

        self.workspace = os.path.abspath(
            cfg["agent"].get("workspace", DEFAULT_WORKSPACE)
        )
        memory_cfg = dict(cfg["memory"])
        memory_cfg.setdefault("workspace", self.workspace)
        backend = (memory_cfg.get("backend") or "json").lower().strip()
        if backend == "sqlite":
            sqlite_cfg = dict(memory_cfg)
            db_path = sqlite_cfg.pop("sqlite_db_path", "") or ""
            if db_path:
                sqlite_cfg["db_path"] = db_path
            self.memory = SqliteSessionMemory(sqlite_cfg)

            # One-time best-effort migration from legacy JSON memory.
            try:
                import json as _json
                import os as _os
                from datetime import datetime as _dt

                legacy_path = _os.path.join(
                    self.cfg["agent"].get("workspace", DEFAULT_WORKSPACE), "memory.json"
                )
                if legacy_path and _os.path.exists(legacy_path):
                    # Only migrate into a fresh session with no messages.
                    if not self.memory.get_messages():
                        with open(legacy_path, "r", encoding="utf-8") as handle:
                            data = _json.load(handle) or {}
                        msgs = data.get("messages", []) or []
                        if msgs:
                            self.memory.import_messages(msgs)
                            bak = (
                                legacy_path
                                + ".bak_"
                                + _dt.now().strftime("%Y%m%d_%H%M%S")
                            )
                            try:
                                _os.replace(legacy_path, bak)
                            except Exception:
                                pass
            except Exception:
                pass
        else:
            self.memory = memory.SessionMemory(memory_cfg)

        self.tools = ToolRegistry(
            cfg, memory_backend=self.memory, confirm_handler=confirm_handler
        )

        # Audit logging (no chat content)
        logging_cfg = self.cfg.get("logging", {}) or {}
        audit_enabled = bool(logging_cfg.get("audit_enabled", True))
        audit_dir = logging_cfg.get("audit_dir") or os.path.join(
            self.cfg["agent"].get("workspace", DEFAULT_WORKSPACE), "logs"
        )
        if not os.path.isabs(audit_dir):
            audit_dir = os.path.join(BASE_DIR, audit_dir)
        audit_fmt = (logging_cfg.get("audit_format") or "jsonl").lower().strip()
        if audit_fmt not in ("jsonl", "log", "both"):
            audit_fmt = "jsonl"
        self.audit = AuditLogger(audit_dir, enabled=audit_enabled, fmt=audit_fmt)
        self.session_id = getattr(
            self.memory, "session_id", datetime.now().strftime("%Y%m%d_%H%M%S")
        )
        try:
            self.audit.session_start(
                session_id=self.session_id,
                provider=self.client.provider,
                model=self.client.model,
                workspace=self.cfg["agent"].get("workspace", DEFAULT_WORKSPACE),
            )
        except Exception:
            pass
        self.max_iter = cfg["agent"]["max_iterations"]
        self.verbose = cfg["agent"]["verbose_thinking"]
        self.confirm = cfg["agent"].get("auto_confirm", True)
        self.hot_reload_enabled = cfg["agent"].get("hot_reload", True)
        self.autonomy_cfg = cfg.get("autonomy", {})
        self.task_tracker = TaskTracker(
            cfg["agent"].get("workspace", DEFAULT_WORKSPACE), session_id=self.session_id
        )

        # Autopilot: minimize human interaction while staying inside safety rails.
        if self.autonomy_cfg.get("autopilot", False):
            self.confirm = True

        # Heuristics and Limits
        self.heuristics = self.cfg.get("heuristics", {})
        self.performance = self.cfg.get("performance", {})
        self.enable_cov = self.cfg["agent"].get("enable_cov", True)
        self.cov_model = self.heuristics.get("cov_model")

        # Dynamic hot-reload tracking
        self.mtimes: Dict[str, float] = (
            self._get_mtimes() if self.hot_reload_enabled else {}
        )
        self._last_reload_check = time.time()
        self._reload_throttle = 2.0  # seconds
        self._cached_system = None

    def _get_mtimes(self) -> Dict[str, float]:
        mtimes: Dict[str, float] = {}
        tracked_dirs = [
            BASE_DIR,
            os.path.join(BASE_DIR, "core"),
            os.path.join(BASE_DIR, "tools"),
            os.path.join(BASE_DIR, "scripts"),
        ]
        try:
            for directory in tracked_dirs:
                if not os.path.isdir(directory):
                    continue
                for root, dirs, files in os.walk(directory):
                    dirs[:] = [
                        d for d in dirs if d != "__pycache__" and not d.startswith(".")
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
                print(
                    f"{C.YELLOW}↻  Config changed: config.yaml. Refreshing settings...{C.RESET}"
                )
                self.cfg = load_config()
                # Update agent properties
                self.max_iter = self.cfg["agent"]["max_iterations"]
                self.verbose = self.cfg["agent"]["verbose_thinking"]
                self.confirm = self.cfg["agent"].get("auto_confirm", True)
                self.hot_reload_enabled = self.cfg["agent"].get("hot_reload", True)
                self.autonomy_cfg = self.cfg.get("autonomy", {})

                # Re-init client if provider changed
                provider = self.cfg["agent"].get("provider", "ollama").lower()
                if provider == "nvidia":
                    self.client = NvidiaClient(self.cfg)
                elif provider == "gemini":
                    self.client = GeminiClient(self.cfg)
                elif provider == "groq":
                    self.client = GroqClient(self.cfg)
                else:
                    self.client = OllamaClient(self.cfg)
                self.task_tracker = TaskTracker(
                    self.cfg["agent"].get("workspace", DEFAULT_WORKSPACE),
                    session_id=self.session_id,
                )

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
                                except Exception:
                                    pass

                # Standard reload for other changed modules
                for f in changed_files:
                    if f.endswith(".py"):
                        mod_name = os.path.splitext(f)[0].replace(os.sep, ".")
                        if mod_name in sys.modules:
                            print(
                                f"{C.YELLOW}↻  File changed: {f}. Reloading module...{C.RESET}"
                            )
                            importlib.reload(sys.modules[mod_name])

            # Re-initialize tool registry
            import core.tool_registry

            importlib.reload(core.tool_registry)
            self.tools = core.tool_registry.ToolRegistry(self.cfg)
            self.mtimes = new_mtimes or self._get_mtimes()
            self._cached_system = None  # Ensure cache is cleared
            print_success("Environment reloaded successfully.")

        except Exception as e:
            print_error(f"Failed to reload: {e}")
            self.mtimes = new_mtimes or self._get_mtimes()

    def build_system(self) -> str:
        # Get unified system prompt from config
        raw_prompt = self.cfg.get("prompts", {}).get(
            "system_prompt", "You are an AI assistant."
        )
        tools_block = self.tools.tool_descriptions()

        # Inject Active Task Memory from disk (User suggestion)
        task_memory = ""
        if self.task_tracker.current:
            c = self.task_tracker.current
            task_memory = (
                "\n\n### ACTIVE_TASK_MEMORY (Loaded from session file)\n"
                f"GOAL: {c.get('goal', 'N/A')}\n"
                f"OBJECTIVE: {c.get('objective', 'N/A')}\n"
                f"PLAN: {', '.join(c.get('plan', []))}\n"
                f"CURRENT_STEP: {c.get('current_step', 'N/A')}\n"
                f"ITERATION: {c.get('iteration', 0)}\n"
                f"LAST_ACTION: {c.get('last_action', 'N/A')}\n"
                f"LAST_OBSERVATION: {c.get('last_observation', 'N/A')}\n"
                "-------------------------------------------\n"
            )

        # Avoid KeyError crashes from unrelated braces in prompt text.
        if "{tool_descriptions}" in raw_prompt:
            system = raw_prompt.replace("{tool_descriptions}", tools_block)
        else:
            system = f"{raw_prompt}\n\nAVAILABLE_TOOLS:\n{tools_block}"

        # Inject Thinking Canvas (Working Memory)
        canvas_block = ""
        if self.tools._canvas:
            canvas_block = (
                "\n\n### THINKING_CANVAS (Current Draft/Working Memory)\n"
                f"{self.tools._canvas}\n"
                "-------------------------------------------\n"
            )

        # Inject Shadow Mode Warning
        shadow_block = ""
        if self.tools.shadow_mode:
            shadow_block = (
                "\n\n### ⚠ WARNING: SHADOW MODE (DRY RUN) ACTIVE\n"
                "You are currently in SHADOW MODE. Your 'Dangerous' actions (write, delete, run) will be SIMULATED.\n"
                "Read-only tools still work normally. Use this mode to test your logic safely.\n"
                "-------------------------------------------\n"
            )

        # Inject Workspace Path
        workspace_block = (
            f"\n\n### WORKSPACE_ROOT\n"
            f"Your absolute workspace root is: {self.workspace}\n"
            "Use this for all file operations. If a path is relative, it is relative to this root.\n"
            "-------------------------------------------\n"
        )

        return system + task_memory + canvas_block + shadow_block + workspace_block

    def verify_action(self, tool_name: str, args: Dict, context: str) -> (bool, str):
        """
        Performs a 'mental simulation' to verify if the tool call is valid and necessary.
        """
        # Hard Check: Tool Existence
        if tool_name not in self.tools.registry:
            return False, f"Tool '{tool_name}' is not in the registry. Check /tools for available capabilities."

        # Soft Check: Model Verification
        prompt = (
            "You are the Technical Verification Monitor for AgenticOs.\n"
            "Your ONLY job is to verify the technical validity and safety of the proposed action.\n\n"
            f"TOOL: {tool_name}\n"
            f"ARGS: {args}\n\n"
            "CONTEXT (Recent history):\n"
            f"{context}\n\n"
            "STRICT VERIFICATION RULES:\n"
            "1. TECHNICAL VALIDITY: Are the arguments logically sound? (e.g. if reading a file, has it been identified/created?)\n"
            "2. ANTI-LOOP: Is the agent repeating the EXACT same command that just failed or yielded no new info?\n"
            "3. NO STRATEGY JUDGMENT: Do NOT reject an action because it is 'insufficient' to solve the whole task. "
            "Tasks are solved via MANY small, sequential steps. Sequential searches are VALID.\n"
            f"4. TOOL EXISTENCE: Assume the tool '{tool_name}' is valid and registered. Do NOT reject based on tool name existence.\n\n"
            "REPLY FORMAT:\n"
            "If the action is technically valid, reply ONLY with 'OK'.\n"
            "If invalid, broken, or a loop, reply 'REJECT: [concise technical reason]'."
        )

        try:
            # Use cov_model if specified, otherwise use active model
            original_model = self.client.model
            if self.cov_model:
                self.client.model = self.cov_model

            # Use a minimal message history for speed
            verification_msgs = [{"role": "user", "content": prompt}]
            response = self.client.chat(verification_msgs, system="You are a strict verification monitor.")

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
        control_markers = (
            "OBJECTIVE:",
            "TASK:",
            "PLAN:",
            "CURRENT_STEP:",
            "STRATEGY:",
            "ACTION:",
            "OBSERVATION:",
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
        run_started_ts = time.time()
        original_user_input = user_input
        if self.memory.turn_count == 0:
            try:
                sys_info = self.tools.term.system_info()
                user_input = f"[System Context: {sys_info.replace(chr(10), ' ')}]\n\n{user_input}"
            except Exception:
                pass

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
                print_error(f"Failed to load preferences: {e}")

        if self.autonomy_cfg.get("task_tracking", True):
            should_start_new = True
            if (
                self.task_tracker.current
                and self.task_tracker.current.get("status") == "running"
            ):
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
                if hasattr(self.memory, "start_task") and self.task_tracker.current:
                    try:
                        self.memory.start_task(
                            self.task_tracker.current["task_id"], original_user_input
                        )
                    except Exception:
                        pass

        self.memory.add("user", user_input)
        messages = self.memory.get_messages()
        last_response = None
        repetition_count = 0
        last_action_signature = None
        repeated_action_count = 0
        no_action_count = 0
        minimal_clarifications = self.autonomy_cfg.get("minimal_clarifications", True)

        for iteration in range(1, self.max_iter + 1):
            self.check_reload()
            system = self.build_system()  # Recalculate every iteration for hot-reload

            # Detect repetitive loops
            if repetition_count >= 2:
                repetition_count = 0
                reminder = "You're repeating the same approach. Try a COMPLETELY DIFFERENT strategy."
                messages.append({"role": "user", "content": reminder})
                print(
                    f"{C.YELLOW}⚠  Repetition detected. Suggesting alternative approach.{C.RESET}"
                )

            # Warn if iterations getting high
            warning_threshold = self.heuristics.get("iteration_warning_threshold", 20)
            if iteration > warning_threshold and iteration % 10 == 0:
                print(
                    f"{C.YELLOW}⚠  High iteration count ({iteration}). Consider FINAL ANSWER.{C.RESET}"
                )

            pulse_line(60)
            print(f"{C.DIM}Iteration {iteration}/{self.max_iter}{C.RESET}")

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
                    print(
                        f"{C.YELLOW}⚠  Attempting auto-fallback to: {new_model}{C.RESET}"
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
                        "content": (
                            "Your last message was empty. "
                            "Respond NOW with one of the required formats and include ACTION if any tool is needed."
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
                            print(
                                f"{C.YELLOW}⚠  Empty-loop fallback to: {new_model}{C.RESET}"
                            )
                            self.client.model = new_model
                            no_action_count = 0
                    except Exception:
                        pass
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
                        "Please respond with one of these: "
                        "1) FINAL ANSWER: ... "
                        "2) OBJECTIVE/PLAN/CURRENT_STEP/ACTION "
                        "3) TASK/CONTEXT/STRATEGY/ACTION"
                    )
                    # In autopilot/minimal-clarifications mode, keep nudges short and action-oriented.
                    nudge = obs if minimal_clarifications else f"Clarification: {obs}"
                    messages.append({"role": "user", "content": nudge})
                    self.memory.add("assistant", response)
                    self.memory.add("user", nudge)
                    continue

            actions = parse_actions(response)

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
                        verification_context = "\n".join([f"{m['role'].upper()}: {m['content'][:500]}" for m in messages[-3:]])
                        verification_context += f"\nASSISTANT: {response[:500]}"
                        verified, reason = self.verify_action(tool_name, args, verification_context)
                        if not verified:
                            obs = f"Mental Verification Failed: {reason}"
                            print_warning(obs)
                            observations.append(obs)
                            continue

                    if self.autonomy_cfg.get("task_tracking", True):
                        self.task_tracker.record_action(tool_name, args)

                    # Optional confirmation for destructive actions
                    if (self.cfg["rules"].get("require_confirm_destructive") and not self.confirm):
                        destructive = {"delete_file", "delete_dir", "kill_process", "run_command", "run_script"}
                        if tool_name in destructive:
                            try:
                                ans = input(f"\n{C.RED}⚠  Confirm destructive '{tool_name}'? [y/N]: {C.RESET}").strip().lower()
                                if ans != "y":
                                    observations.append(f"Action '{tool_name}' cancelled by user.")
                                    continue
                            except (KeyboardInterrupt, EOFError):
                                print_info("\nCancelled.")
                                return

                    import time as _time
                    started = _time.time()
                    obs = self.tools.call(tool_name, args)
                    ended = _time.time()
                    observations.append(str(obs or "Done."))

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
                            tool_args=_json.dumps(args, ensure_ascii=False)
                            if isinstance(args, (dict, list))
                            else str(args),
                            started_ts=started,
                            ended_ts=ended,
                            success=ok,
                            validation=validation,
                            observation_preview=obs_text,
                        )
                    except Exception as exc:
                        try:
                            self.audit.error(self.session_id, "audit.tool_call", str(exc))
                        except Exception:
                            pass

                    # Persist tool events + artifacts for SQLite memory backend.
                    if hasattr(self.memory, "record_tool_event"):
                        try:
                            import json as _json

                            self.memory.record_tool_event(
                                tool_name=tool_name,
                                tool_args=_json.dumps(args, ensure_ascii=False)
                                if isinstance(args, (dict, list))
                                else str(args),
                                observation=str(obs),
                            )
                        except Exception:
                            pass

                    if hasattr(self.memory, "record_artifact"):
                        try:
                            self._record_artifacts_from_tool(tool_name, args)
                        except Exception:
                            pass

                    if hasattr(self.memory, "update_task") and self.task_tracker.current:
                        try:
                            self.memory.update_task(self.task_tracker.current["task_id"])
                        except Exception:
                            pass
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
                    max_obs_chars = int(self.cfg.get("agent", {}).get("max_observation_chars", 12000))
                except Exception:
                    max_obs_chars = 12000
                
                if max_obs_chars and len(combined_obs) > max_obs_chars:
                    head_n = int(max_obs_chars * 0.7)
                    tail_n = max_obs_chars - head_n
                    combined_obs = combined_obs[:head_n] + "\n... [TRUNCATED] ...\n" + (combined_obs[-tail_n:] if tail_n > 0 else "")

                messages.append({"role": "assistant", "content": response})
                messages.append({"role": "user", "content": f"OBSERVATION: {combined_obs}"})
                self.memory.add("assistant", response)
                self.memory.add("user", f"OBSERVATION: {combined_obs}")
                continue

            if direct_response and not has_final_answer(response):
                response = f"FINAL ANSWER: {response}"

            if has_final_answer(response):
                # ── Artifact Persistence Guardrail ──────────────────────────────────
                # If the agent mentions saving/writing/creating but hasn't called a tool to do so recently, nudge it.
                resp_lower = response.lower()
                mentions_save = any(kw in resp_lower for kw in ["save", "write", "create", "update", "persist", "report", "analysis", "content"])
                
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
                    
                    persistence_tools = {"write_file", "append_file", "create_plugin", "write_json", "write_csv", "save_to_canvas"}
                    persisted = any(t in recent_actions for t in persistence_tools)
                    
                    if not persisted:
                        # Disabled heuristic: Was forcing write_file for long responses, but wastes API quota.
                        # if len(response) > 1000:
                        #     print_warning("Persistence Guardrail: Model provided a long response but didn't call write_file.")
                        pass

                print(f"\n{C.GREEN}{C.BOLD}{'═' * 60}")
                print("  FINAL ANSWER")
                print(f"{'═' * 60}{C.RESET}")

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
                        except Exception:
                            convo = (system or "") + "\n" + (original_user_input or "")
                        down = _est_tokens(convo)
                        up = _est_tokens(response or "")
                        print_info(
                            f"Time: {elapsed_s:.1f}s | Tokens (est) down={down} up={up}"
                        )
                    except Exception:
                        pass

                    # Artifact-first workflow: persist a per-session result artifact.
                    try:
                        ws = self.cfg["agent"].get("workspace", DEFAULT_WORKSPACE)
                        if not os.path.isabs(ws):
                            ws = os.path.join(BASE_DIR, ws)
                        # Use session_id for the report folder (one per session, not per iteration)
                        session_report_dir = os.path.join(
                            ws, "reports", str(self.session_id)
                        )
                        os.makedirs(session_report_dir, exist_ok=True)
                        # Append to result.md for this session (multiple answers can be added)
                        out_path = os.path.join(session_report_dir, "result.md")
                        is_new = not os.path.exists(out_path)
                        with open(out_path, "a", encoding="utf-8") as handle:
                            if is_new:
                                handle.write("# Session Report\n\n")
                                handle.write("## Session Metadata\n\n")
                                handle.write("| Field | Value |\n")
                                handle.write("|-------|-------|\n")
                                handle.write(
                                    f"| **Session ID** | `{self.session_id}` |\n"
                                )
                                handle.write(
                                    f"| **Provider** | {self.client.provider} |\n"
                                )
                                handle.write(f"| **Model** | `{self.client.model}` |\n")
                                handle.write(
                                    f"| **Started** | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} |\n"
                                )
                                handle.write("\n")

                            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            goal = "Task"
                            if (
                                self.task_tracker.current
                                and self.task_tracker.current.get("goal")
                            ):
                                goal = self.task_tracker.current.get("goal")

                            handle.write(f"## COMPLETED [{ts}] {goal}\n\n")
                            handle.write(final_ans.strip() + "\n\n")
                            handle.write("---\n\n")
                        try:
                            self.memory.record_artifact(
                                out_path, action="final_answer", kind="report"
                            )
                        except Exception:
                            pass
                    except Exception:
                        pass

                # Send notification per rule #9
                try:
                    self.tools.ui.send_notification(
                        "AgenticOs", "Task completed successfully."
                    )
                except Exception:
                    pass

                self.memory.add("assistant", response)
                if self.autonomy_cfg.get("task_tracking", True):
                    self.task_tracker.complete(final_ans or response)
                if hasattr(self.memory, "set_outcome"):
                    try:
                        next_steps = ""
                        if self.task_tracker.current and self.task_tracker.current.get(
                            "plan"
                        ):
                            next_steps = "\n".join(
                                self.task_tracker.current.get("plan", [])[-3:]
                            )
                        self.memory.set_outcome(
                            final_answer=final_ans or response, next_steps=next_steps
                        )
                    except Exception:
                        pass
                if hasattr(self.memory, "set_summary") and self.cfg.get(
                    "memory", {}
                ).get("auto_summarize", True):
                    try:
                        summary = f"Goal: {original_user_input.strip()}\nResult: {(final_ans or '').strip()}"
                        self.memory.set_summary(summary.strip())
                    except Exception:
                        pass
                if hasattr(self.memory, "complete_task") and self.task_tracker.current:
                    try:
                        next_steps = ""
                        if self.task_tracker.current.get("plan"):
                            next_steps = "\n".join(
                                self.task_tracker.current.get("plan", [])[-3:]
                            )
                        self.memory.complete_task(
                            self.task_tracker.current["task_id"],
                            final_answer=final_ans or response,
                            next_steps=next_steps,
                            summary=f"Goal: {original_user_input.strip()}",
                        )
                    except Exception:
                        pass
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
                        "Stall detected: produce an ACTION (tool call) or FINAL ANSWER. "
                        "Update PLAN and CURRENT_STEP, then choose a concrete next action."
                    )
                    print_warning("Stall detected. Requesting replan.")
                    if self.autonomy_cfg.get("task_tracking", True):
                        self.task_tracker.note_stall(stall_obs)
                    messages.append({"role": "user", "content": stall_obs})
                    self.memory.add("user", stall_obs)
                continue

        if self.autonomy_cfg.get("task_tracking", True):
            self.task_tracker.fail(
                f"Reached max iterations ({self.max_iter}) without a final answer."
            )
        print_error(f"Reached max iterations ({self.max_iter}) without a final answer.")
        try:
            self.audit.session_end(self.session_id, status="max_iterations")
        except Exception:
            pass
        if hasattr(self.memory, "set_outcome"):
            try:
                self.memory.set_outcome(final_answer="", next_steps="")
            except Exception:
                pass

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
        "/config": "Show current config",
        "/history": "Show conversation history",
        "/version": "Show version info",
        "/shadow": "Toggle Shadow Mode (Dry Run)",
        "/exit": "Exit AgenticOs",
    }

    def __init__(self):
        self.cfg = load_config()
        self.agent = Agent(self.cfg, confirm_handler=self.handle_security_confirmation)
        self.running = True

    def handle_security_confirmation(self, path: str, operation: str) -> bool:
        """Confirm action with user (CLI implementation)."""
        print("\n\033[91m🛑 SECURITY GUARDRAIL\033[0m")
        print(
            f"The agent is attempting a \033[1m{operation.upper()}\033[0m action outside the workspace."
        )
        print(f"Target Path: \033[36m{path}\033[0m")
        print(
            "\033[90m(You can allow this once, or modify config.yaml to change security rules)\033[0m"
        )
        try:
            ans = input("\nDo you allow this specific action? [y/N]: ").strip().lower()
            return ans == "y"
        except (KeyboardInterrupt, EOFError):
            return False

    def select_provider(self, force: bool = False):
        providers = ["ollama", "nvidia", "gemini", "groq", "openai", "openrouter", "github", "deepseek"]
        current = (self.cfg.get("agent", {}).get("provider") or "ollama").lower()

        print(f"\n{C.CYAN}{C.BOLD}Providers:{C.RESET}")
        for i, p in enumerate(providers, 1):
            marker = f" {C.GREEN}◀ current{C.RESET}" if p == current else ""
            print(f"  {C.BOLD}{i}.{C.RESET} {p}{marker}")
        if not force:
            print(f"\n  {C.BOLD}0.{C.RESET} Keep current ({current})")

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
            except (ValueError, KeyboardInterrupt, EOFError):
                if not force:
                    return
                print_error("Selection required.")
            print_error("Invalid selection.")

    def select_model(self, force=False):
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

        print(
            f"\n{C.CYAN}{C.BOLD}Available {self.agent.client.provider.capitalize()} Models:{C.RESET}"
        )
        for i, m in enumerate(models, 1):
            marker = (
                f" {C.GREEN}◀ current{C.RESET}" if m == self.agent.client.model else ""
            )
            print(f"  {C.BOLD}{i}.{C.RESET} {m}{marker}")

        if not force:
            print(f"\n  {C.BOLD}0.{C.RESET} Keep current ({self.agent.client.model})")

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
                    print(f"\n{C.DIM}Installed Ollama Models (local):{C.RESET}")
                    for m in ollama_models[:60]:
                        print(f"  {m}")
                    if len(ollama_models) > 60:
                        print(f"  {C.DIM}... ({len(ollama_models) - 60} more){C.RESET}")
        except Exception:
            # Silent: this is a convenience listing and should not block selection.
            pass

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
            except (ValueError, KeyboardInterrupt, EOFError):
                if not force:
                    break
                print_error("Selection required.")
            print_error("Invalid selection.")

    def handle_command(self, cmd: str):
        parts = cmd.strip().split(None, 1)
        base = parts[0].lower()

        if base == "/help":
            print(f"\n{C.CYAN}{C.BOLD}AgenticOs Commands:{C.RESET}")
            for c, d in self.COMMANDS.items():
                print(f"  {C.YELLOW}{c:<12}{C.RESET} {d}")

        elif base == "/model":
            self.select_model()

        elif base == "/provider":
            self.select_provider()

        elif base == "/models":
            models = self.agent.client.list_models()
            if models:
                print(f"\n{C.CYAN}Available models:{C.RESET}")
                for m in models:
                    active = (
                        f" {C.GREEN}◀ active{C.RESET}"
                        if m == self.agent.client.model
                        else ""
                    )
                    print(f"  {m}{active}")
            else:
                err = getattr(self.agent.client, "last_list_error", "")
                if err:
                    print_error(f"No models found. ({err})")
                else:
                    print_error("No models found.")

        elif base == "/tools":
            print(
                f"\n{C.CYAN}{C.BOLD}Available Tools ({len(self.agent.tools.registry)}):{C.RESET}"
            )
            for name, info in self.agent.tools.registry.items():
                print(f"  {C.YELLOW}{name:<25}{C.RESET} {C.DIM}{info['desc']}{C.RESET}")

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
            print(f"\n{C.CYAN}{C.BOLD}Doctor Checks:{C.RESET}")
            # 1) Config parse already succeeded if we got here.
            print_success("config.yaml: OK (parsed)")
            # 2) Memory backend writable?
            try:
                mem = self.agent.memory
                if hasattr(mem, "healthcheck"):
                    print(mem.healthcheck())
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
            print(f"\n{C.CYAN}Session Memory:{C.RESET}\n{self.agent.memory.summary()}")

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

        elif base == "/reload":
            self.agent.mtimes = {}  # Force reload
            self.agent.check_reload()

        elif base == "/config":
            print(f"\n{C.CYAN}Current Config:{C.RESET}")
            print(yaml.dump(self.cfg, default_flow_style=False))

        elif base == "/history":
            msgs = self.agent.memory.get_messages()
            print(f"\n{C.CYAN}Conversation History ({len(msgs)} messages):{C.RESET}")
            for msg in msgs[-20:]:
                role = msg["role"].upper()
                color = C.BLUE if role == "USER" else C.GREEN
                preview = msg["content"][:200].replace("\n", " ")
                print(f"  {color}{C.BOLD}{role:<12}{C.RESET} {C.DIM}{preview}{C.RESET}")

        elif base == "/version":
            provider = self.agent.client.provider
            print(f"\n{C.CYAN}AgenticOs v1.1.0{C.RESET}")
            print(f"  Provider : {provider}")
            print(f"  Model    : {self.agent.client.model}")
            if hasattr(self.agent.client, "base_url"):
                print(f"  Endpoint : {self.agent.client.base_url}")
            print(f"  Tools    : {len(self.agent.tools.registry)}")
            print(f"  Session  : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        elif base in ("/exit", "/quit", "/q"):
            try:
                # Do NOT wipe persistent memory on exit. Use /clear for that.
                if not bool(self.cfg.get("memory", {}).get("enable_persistence", True)):
                    self.agent.memory.clear()
                    print(f"\n{C.CYAN}Goodbye. Session memory wiped.{C.RESET}")
                else:
                    print(f"\n{C.CYAN}Goodbye.{C.RESET}")
            except Exception:
                print(f"\n{C.CYAN}Goodbye.{C.RESET}")
            try:
                if hasattr(self.agent, "audit"):
                    self.agent.audit.session_end(
                        getattr(self.agent, "session_id", "unknown"), status="exit"
                    )
            except Exception:
                pass
            self.running = False

        else:
            print_error(f"Unknown command: {base}. Type /help.")

    def run(self):
        banner()

        autonomy_cfg = self.cfg.get("autonomy", {})
        if autonomy_cfg.get("startup_provider_prompt", False):
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
            key_preview = (
                (self.agent.client.api_key[:8] + "...")
                if self.agent.client.api_key
                else "NOT SET"
            )
            print_success("Google Gemini provider connected.")
            print_info(f"API key: {key_preview}")
        else:
            key_preview = (
                (self.agent.client.api_key[:8] + "...")
                if self.agent.client.api_key
                else "NOT SET"
            )
            print_success("Nvidia NIM provider connected.")
            print_info(f"API key: {key_preview}")

        if autonomy_cfg.get("startup_model_prompt", False):
            # Non-forced by default so startup can remain quick for autopilot runs.
            self.select_model(force=False)

        print_success(
            f"Tools loaded: {len(self.agent.tools.registry)} tools available."
        )
        print(
            f"\n{C.DIM}Type your task, or /help for commands. Ctrl+C or /exit to quit.{C.RESET}\n"
        )

        try:
            readline.parse_and_bind("tab: complete")
        except Exception:
            pass

        while self.running:
            try:
                raw = input(f"{C.BOLD}AgenticOs{C.RESET} {C.CYAN}❯{C.RESET} ").strip()
            except KeyboardInterrupt:
                print(f"\n{C.CYAN}Interrupted. Type /exit to quit.{C.RESET}")
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
                    print(f"\n{C.YELLOW}Task interrupted.{C.RESET}")
                except Exception as e:
                    print_error(f"Unexpected error: {e}")
                    traceback.print_exc()


def main():
    try:
        CLI().run()
    except RuntimeError as e:
        print(f"\n\033[91mError: {e}\033[0m")
        print("\033[33mAdd the missing key to your .env file and restart.\033[0m\n")
        raise SystemExit(1)


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    main()
