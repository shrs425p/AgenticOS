def _get_base_dir() -> str:
    import kernel.cli as runtime
    return getattr(runtime, "BASE_DIR", None)

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


class Agent:
    def __init__(self, cfg: dict, confirm_handler: Optional[Callable] = None):
        self.cfg = cfg
        self.confirm_handler = confirm_handler

        self._load_agent_settings()
        
        # Profile host hardware at startup
        from kernel.resources import profile_hardware
        self.hardware_profile = profile_hardware()
        
        self._init_client()
        self._setup_workspace()
        
        # Initialize CheckpointManager using self.workspace
        from kernel.checkpoint import CheckpointManager
        self.checkpoint_manager = CheckpointManager(self.workspace)
        
        # Initialize retry classifier and stall monitor
        from kernel.triage import RetryClassifier
        from kernel.stalls import StallMonitor
        self.retry_classifier = RetryClassifier()
        self.stall_monitor = StallMonitor()
        
        self.active_checkpoint_id = None
        self.active_checkpoint_phase = None

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
        import kernel.cli as runtime
        client_cls = getattr(runtime, client_name)
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
        import kernel.cli as runtime
        self.memory = runtime.SqliteSessionMemory(sqlite_cfg)

        # Preserve the security zone settings from the old guard if it exists
        old_guard_state = None
        if hasattr(self, "ops") and getattr(self.ops, "guard", None) is not None:
            old_guard = self.ops.guard
            old_guard_state = {
                "enabled": old_guard.enabled,
                "require_hitm": old_guard.require_hitm,
                "read_only": getattr(old_guard, "read_only", False)
            }

        import kernel.cli as runtime
        self.ops = runtime.ToolRegistry(
            self.cfg, memory_backend=self.memory, confirm_handler=self.confirm_handler
        )

        # Restore the security zone settings onto the new guard
        if old_guard_state and getattr(self.ops, "guard", None) is not None:
            self.ops.guard.enabled = old_guard_state["enabled"]
            self.ops.guard.require_hitm = old_guard_state["require_hitm"]
            self.ops.guard.read_only = old_guard_state["read_only"]

    def _init_audit_and_task_tracker(self) -> None:
        logging_cfg = self.cfg.get("logging", {}) or {}
        audit_enabled = bool(logging_cfg.get("audit_enabled", True))
        audit_dir = logging_cfg.get("audit_dir") or os.path.join(self.workspace, "logs")
        if not os.path.isabs(audit_dir):
            audit_dir = os.path.join(_get_base_dir(), audit_dir)
        audit_fmt = (logging_cfg.get("audit_format") or "jsonl").lower().strip()
        import kernel.cli as runtime
        self.audit = runtime.AuditLogger(
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
        import kernel.cli as runtime
        self.context_engine = runtime.ContextEngine(self)
        self.context_engine.set_compact_threshold(self.hardware_profile.compact_history_threshold)
        import kernel.cli as runtime
        mm = runtime.initialize_memory_manager(self.workspace, self.client, self.cfg)
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

    def _reload_cfg(self) -> None:
        old_workspace = getattr(self, "workspace", None)
        self.cfg = load_cfg(force_reload=True)
        self._load_agent_settings()
        self._init_client()

        new_workspace = os.path.abspath(
            self.cfg["agent"].get("workspace", DEFAULT_WORKSPACE)
        )
        if new_workspace != old_workspace:
            self.workspace = new_workspace
            self._setup_workspace()
        else:
            # Reinitialize memory if memory cfg changed and workspace path is unchanged
            self._setup_workspace()

        from kernel.checkpoint import CheckpointManager
        self.checkpoint_manager = CheckpointManager(self.workspace)

        self.task_tracker = TaskTracker(
            self.cfg["agent"].get("workspace", DEFAULT_WORKSPACE),
            session_id=self.session_id,
            cfg=self.cfg,
        )

    def _get_mtimes(self) -> Dict[str, float]:
        mtimes: Dict[str, float] = {}
        tracked_dirs = [
            os.path.join(_get_base_dir(), d)
            for d in self.cfg.get("hot_reload", {}).get(
                "tracked_dirs", ["kernel", "ops", "scripts"]
            )
        ]
        if _get_base_dir() not in tracked_dirs:
            tracked_dirs.append(_get_base_dir())

        blacklisted_dirs = set(
            self.cfg.get("hot_reload", {}).get(
                "excluded_dirs", DEFAULT_SCAN_EXCLUDED_DIRS
            )
        )
        try:
            for directory in tracked_dirs:
                if not os.path.isdir(directory):
                    continue
                if os.path.basename(os.path.normpath(directory)) in blacklisted_dirs:
                    continue
                for root, dirs, files in os.walk(directory):
                    dirs[:] = [
                        d
                        for d in dirs
                        if not d.startswith(".") and d not in blacklisted_dirs
                    ]
                    for name in files:
                        if not (name.endswith(".py") or name == "cfg.yaml"):
                            continue
                        abs_path = os.path.join(root, name)
                        rel_path = os.path.relpath(abs_path, _get_base_dir())
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
            cfg_changed = "cfg.yaml" in changed_files
            py_changed = any(f.endswith(".py") for f in changed_files)

            if cfg_changed:
                logger.info(
                    f"{C.YELLOW}↻  Config changed: cfg.yaml. Refreshing settings...{C.RESET}"
                )
                self._reload_cfg()

            if py_changed:
                import importlib

                # If any tool-related file changed, force a reload of the registry and major mixins
                for f in changed_files:
                    if "ops" in f or "kernel/registry" in f:
                        for mod in [
                            "ops.web_ops",
                            "kernel.registry",
                            "ops.web.spotify",
                            "ops.web.browser",
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
            import kernel.registry

            importlib.reload(kernel.registry)
            self.ops = kernel.registry.ToolRegistry(
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

    def _extract_roadmap_phases(self) -> list:
        phases = []
        roadmap_path = os.path.join(self.workspace, ".planning", "ROADMAP.md")
        if os.path.exists(roadmap_path):
            try:
                with open(roadmap_path, "r", encoding="utf-8") as f:
                    content = f.read()
                # Find lines like "- [ ] **Phase N: Name**" or "- [x] **Phase N: Name**"
                matches = re.findall(r"-\s*\[([ xX])\]\s*\*\*Phase\s*(\d+):\s*([^*]+)\*\*", content)
                for status_char, num, name in matches:
                    status = "complete" if status_char.lower() == "x" else "pending"
                    phases.append({
                        "name": f"Phase {num}: {name.strip()}",
                        "status": status,
                        "steps": [],
                        "result": None
                    })
            except Exception as e:
                print_warning(f"Warning: Failed to parse ROADMAP.md for phases: {e}")
        # Fallback to default phases if none found
        if not phases:
            phases = [
                {"name": "Phase 1: Core Security and Code Quality Foundation", "status": "pending", "steps": []},
                {"name": "Phase 2: Performance and LLM Integration Layer", "status": "pending", "steps": []},
                {"name": "Phase 3: Platform OS Control and Autonomy Framework", "status": "pending", "steps": []},
                {"name": "Phase 4: Memory, Extensibility, and Resiliency Harness", "status": "pending", "steps": []},
            ]
        return phases

    def verify_action(
        self, tool_name: str, args: Dict, context: str
    ) -> Tuple[bool, str]:
        """
        Performs a 'mental simulation' to verify if the tool call is valid and necessary.
        """
        from kernel.dispatch import verify_action
        return verify_action(self, tool_name, args, context)

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
                sys_info = (
                    f"os={platform.system()} {platform.release()} "
                    f"arch={platform.machine()} python={platform.python_version()} "
                    f"cwd={os.getcwd()} pid={os.getpid()}"
                )
                user_input = f"[System Context: {sys_info.replace(chr(10), ' ')}]\n\n{user_input}"
            except Exception as e:
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

        # Initialize SuccessCriteria for the goal
        from kernel.criteria import SuccessCriteria
        self.success_criteria = SuccessCriteria(original_user_input)

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
                # Check for an existing checkpoint matching the goal
                existing_checkpoint = self.checkpoint_manager.load(original_user_input)
                if existing_checkpoint:
                    task_id = existing_checkpoint["task_id"]
                    next_phase = self.checkpoint_manager.next_pending_phase(task_id)
                    if next_phase:
                        resume = False
                        if self.autonomy_cfg.get("autopilot", False):
                            logger.info(f"Autopilot active: resuming task from checkpoint phase '{next_phase['name']}'")
                            resume = True
                        elif self.confirm_handler:
                            checkpoint_json_path = os.path.join(self.checkpoint_manager.checkpoints_dir, f"{task_id}.json")
                            resume = self.confirm_handler(checkpoint_json_path, f"resume_phase_{next_phase['name']}")
                        else:
                            try:
                                ans = input(f"Existing checkpoint found for this task. Resume phase '{next_phase['name']}'? [Y/n]: ").strip().lower()
                                resume = ans not in ("n", "no")
                            except (KeyboardInterrupt, EOFError):
                                resume = False
                                
                        if resume:
                            user_input = f"[Resuming Task from Checkpoint: Phase '{next_phase['name']}']\n\n{original_user_input}"
                            logger.info(f"Resuming task '{task_id}' at phase '{next_phase['name']}'")
                            self.active_checkpoint_id = task_id
                            self.active_checkpoint_phase = next_phase["name"]
                        else:
                            # User declined to resume. Create a new checkpoint.
                            phases = self._extract_roadmap_phases()
                            self.active_checkpoint_id = self.checkpoint_manager.create(original_user_input, phases)
                            self.active_checkpoint_phase = phases[0]["name"]
                    else:
                        # Checkpoint exists but all phases are complete. Create a new one.
                        phases = self._extract_roadmap_phases()
                        self.active_checkpoint_id = self.checkpoint_manager.create(original_user_input, phases)
                        self.active_checkpoint_phase = phases[0]["name"]
                else:
                    phases = self._extract_roadmap_phases()
                    self.active_checkpoint_id = self.checkpoint_manager.create(original_user_input, phases)
                    self.active_checkpoint_phase = phases[0]["name"]

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

        # Update active checkpoint phase to running
        if getattr(self, "active_checkpoint_id", None) and getattr(self, "active_checkpoint_phase", None):
            self.checkpoint_manager.update_phase(
                self.active_checkpoint_id,
                self.active_checkpoint_phase,
                "running"
            )

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
                    symbol = self.ops.get_symbol(tool_name)
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
                                "destructive_ops",
                                [
                                    "delete_file",
                                    "delete_dir",
                                    "kill_process",
                                    "runcommand",
                                    "runscript",
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
                    obs = self.ops.call(tool_name, args)
                    ended = _time.time()
                    elapsed = ended - started

                    obs_text = str(obs or "")
                    ok = infer_success(obs_text)

                    # local transient error retry classifier
                    if not ok:
                        # Parse exit code if any
                        exit_code = None
                        if "exit code" in obs_text.lower():
                            match = re.search(r"exit code:?\s*(\d+)", obs_text, re.IGNORECASE)
                            if match:
                                exit_code = int(match.group(1))
                            else:
                                match = re.search(r"code\s*(\d+)", obs_text, re.IGNORECASE)
                                if match:
                                    exit_code = int(match.group(1))
                        
                        decision = self.retry_classifier.classify(obs_text, exit_code)
                        if decision.action == "retry":
                            retries = 0
                            max_retries = decision.max_retries
                            while retries < max_retries and not ok:
                                print_warning(f"Transient error detected ({decision.reason}). Retrying tool '{tool_name}' (Attempt {retries + 1}/{max_retries})...")
                                started = _time.time()
                                obs = self.ops.call(tool_name, args)
                                ended = _time.time()
                                elapsed = ended - started
                                obs_text = str(obs or "")
                                ok = infer_success(obs_text)
                                retries += 1

                    # check for stalls
                    stall_warning = self.stall_monitor.check_stall(tool_name, elapsed)
                    if stall_warning:
                        print_warning(f"Stall Warning for '{tool_name}' ({stall_warning.category}): took {elapsed:.1f}s (threshold {stall_warning.threshold}s).")
                        print_warning(f"Suggestion: {stall_warning.suggestion}")
                        obs_text += f"\n\n[STALL WARNING: This action took {elapsed:.1f} seconds. {stall_warning.suggestion}]"

                    observations.append(obs_text)

                    ok = False

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

                # Comclie all observations
                comclied_obs = "\n---\n".join(observations)

                # Nudge if the model tried to batch actions (which we now truncate in parse_actions)
                if response.count("ACTION:") > 1:
                    batch_hint = "\n\nHINT: You attempted to call multiple ops. Only the first tool was executed. Please wait for the observation before calling the next tool. Call exactly ONE tool per turn."
                    comclied_obs += batch_hint

                print_observation(comclied_obs)

                # Limit observation length
                try:
                    max_obs_chars = int(
                        self.cfg.get("agent", {}).get(
                            "max_observation_chars",
                            self.heuristics.get("max_observation_chars", 12000),
                        )
                    )
                except ValueError as e:
                    print_warning(f"Warning: Invalid max_observation_chars cfg: {e}")
                    max_obs_chars = 12000

                if max_obs_chars and len(comclied_obs) > max_obs_chars:
                    head_n = int(max_obs_chars * 0.7)
                    tail_n = max_obs_chars - head_n
                    comclied_obs = (
                        comclied_obs[:head_n]
                        + "\n... [TRUNCATED] ...\n"
                        + (comclied_obs[-tail_n:] if tail_n > 0 else "")
                    )

                messages.append({"role": "assistant", "content": response})
                messages.append(
                    {"role": "user", "content": f"OBSERVATION: {comclied_obs}"}
                )
                self.memory.add("assistant", response)
                self.memory.add("user", f"OBSERVATION: {comclied_obs}")
                continue

            if direct_response and not has_final_answer(response):
                response = f"FINAL ANSWER: {response}"

            if has_final_answer(response):
                # Verify SuccessCriteria before terminating
                if getattr(self, "success_criteria", None) and not self.success_criteria.is_met(messages):
                    missing_criteria = [c for c in self.success_criteria.criteria if not any(w.lower() in "\n".join([m.get("content", "") for m in messages if m.get("content")]).lower() for w in re.split(r"\W+", c) if len(w) > 3)]
                    missing_str = ", ".join([f"'{c}'" for c in missing_criteria])
                    nudge_msg = f"OBSERVATION: You attempted to finalize the task, but the success criteria has not been fully verified: {missing_str}. Please execute the necessary verification steps or confirm they have been satisfied before providing the FINAL ANSWER."
                    print_warning(f"Success criteria verification failed. Nudging agent to verify: {missing_str}")
                    messages.append({"role": "assistant", "content": response})
                    messages.append({"role": "user", "content": nudge_msg})
                    self.memory.add("assistant", response)
                    self.memory.add("user", nudge_msg)
                    continue

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

                    persistence_ops = {
                        "write_file",
                        "append_file",
                        "createplugin",
                        "writejson",
                        "writecsv",
                        "save_to_canvas",
                    }
                    persisted = any(t in recent_actions for t in persistence_ops)

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
                    prompt_dump_skernel = sum(
                        marker in low_final
                        for marker in (
                            "available_ops",
                            "workspace_root",
                            "thinking_canvas",
                            "active_task_memory",
                            "### ",
                            "-------------------------------------------",
                        )
                    )
                    if prompt_dump_skernel >= 2:
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
                            ws = os.path.join(_get_base_dir(), ws)
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
                    self.ops.ui.sendnotification("AgenticOs", msg)
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

                    # Extract ops used from tracking
                    ops_used = []
                    if curr_task and curr_task.get("actions_taken"):
                        ops_used = [
                            a.get("tool")
                            for a in curr_task.get("actions_taken", [])
                            if a.get("tool")
                        ]

                    duration_s = max(0.0, time.time() - run_started_ts)
                    tracker_task_id = curr_task.get("task_id") if curr_task else None
                    log_task_completion(
                        goal=goal,
                        final_answer=final_ans or response,
                        ops_used=list(set(ops_used)),
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
                # Mark active checkpoint phase as complete
                if getattr(self, "active_checkpoint_id", None) and getattr(self, "active_checkpoint_phase", None):
                    self.checkpoint_manager.update_phase(
                        self.active_checkpoint_id,
                        self.active_checkpoint_phase,
                        "complete",
                        result=(final_ans or response)
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
            ops_used = []
            goal = "Task"
            curr_task = self.task_tracker.current
            if curr_task:
                ops_used = [
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
                    ops_used=list(set(ops_used)),
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

        Records touched paths for common filesystem ops.
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
            # Pipe format: infer first arg is usually a path for file ops.
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
