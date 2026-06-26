"""Config and path helpers for the AgenticOs runtime."""

import os

import yaml
from kernel.schema import ConfigDict  # typing helper


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CONFIG_LAYERS = [
    "providers.yaml",
    "runtime.yaml",
    "policy.yaml",
    "ops.yaml",
    "storage.yaml",
    "prompts.yaml",
    "endpoints.yaml",
]


def get_path(rel_path: str) -> str:
    """get_path function."""
    return os.path.join(BASE_DIR, rel_path)


def resolve_local_path(path: str, default: str = "") -> str:
    """resolve_local_path function."""
    raw_path = path or default
    expanded = os.path.expandvars(os.path.expanduser(raw_path))
    if not os.path.isabs(expanded):
        expanded = os.path.join(BASE_DIR, expanded)
    return os.path.abspath(expanded)


DEFAULT_WORKSPACE = resolve_local_path(
    os.environ.get("AGENTICOS_WORKSPACE", "workspace")
)

DEFAULT_SCAN_EXCLUDED_DIRS = [
    ".git",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "workspace",
    "data",
    "mock_workspace",
]

# Minimal structure defaults. Actual values come from cfg/*.yaml plus
# root cfg.yaml overrides.
default_structure = {
    "ollama": {},
    "agent": {"workspace": DEFAULT_WORKSPACE},
    "endpoints": {},
    "windows_paths": {},
    "autonomy": {},
    "cloud": {"nvidia": {}},
    "memory": {},
    "rules": {},
    "security": {},
    "logging": {
        "fmt": "jsonl",
        "filenames": {
            "session": "session",
            "ops": "ops",
            "errors": "errors",
            "paths": "paths",
        }
    },
    "ops": {
        "web": {
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36",
        }
    },
    "performance": {
        "max_retries": 5,
        "base_retry_delay": 5.0,
    },
    "context": {
        "workspace_ignore_dirs": DEFAULT_SCAN_EXCLUDED_DIRS.copy(),
    },
    "hot_reload": {
        "tracked_dirs": ["kernel", "ops", "scripts"],
        "excluded_dirs": DEFAULT_SCAN_EXCLUDED_DIRS.copy(),
    },
    "heuristics": {
        "dream_interval_hours": 6,
        "slow_task_threshold_seconds": 120,
        "dream_task_limit": 15,
        "prose_vs_tool_threshold": 120,
        "hot_reload_throttle": 2.0,
        "max_dots_in_response": 50,
        "iteration_warning_threshold": 20,
    },
    "prompts": {
        "reflection": {},
        "verification": {},
        "nudges": {
            "stall_detected": "Stall detected: produce an ACTION (tool call) or FINAL ANSWER. Update PLAN and CURRENT_STEP, then choose a concrete next action."
        },
        "notifications": {
            "task_completed": "Task completed successfully.",
        },
        "session_report": {},
        "dream_cycle": {},
        "file_templates": {},
        "ui_labels": {
            "spinner_message": "Thinking",
            "banner_subtitle": "Autonomous CLI Agent  •  Ollama / Nvidia NIM  •  Session Memory",
        },
        "reporting": {
            "goal_label": "Goal:",
            "result_label": "Result:",
            "max_iter_reached": "Reached max iterations ({max_iter}) without a final answer.",
        }
    },
    "policy": {
        "redaction_patterns": [
            ["(?i)(NVIDIA_API_KEY\\s*=\\s*)([^\\s]+)", "\\1[REDACTED]"],
            ["(?i)(OPENAI_API_KEY\\s*=\\s*)([^\\s]+)", "\\1[REDACTED]"],
            ["(?i)(Authorization:\\s*Bearer\\s+)([A-Za-z0-9._-]+)", "\\1[REDACTED]"],
            ["(?i)(Bearer\\s+)([A-Za-z0-9._-]{12,})", "\\1[REDACTED]"],
            ["(?i)(nvapi-[A-Za-z0-9_-]{8,})", "[REDACTED]"],
        ]
    },
    "timeouts": {
        "browser_nav": 30000,
        "browser_action": 10000,
        "websearch": 15,
        "service_control": 60,
        "package_manager": 60,
        "system_admin": 30,
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base and return base."""
    for key, value in (override or {}).items():
        if (
            isinstance(value, dict)
            and isinstance(base.get(key), dict)
        ):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def _read_yaml_file(path: str) -> dict:
    with open(path, encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Configuration file must contain a mapping: {path}")
    return data


def _load_layered_cfg(root_path: str) -> tuple[dict, dict]:
    """Return (merged_cfg, raw_root_cfg) where raw_root_cfg is the dict
    loaded *only* from root_path before any layer merges."""
    cfg: dict = {}
    cfg_dir = os.path.join(os.path.dirname(root_path), "cfg")
    if os.path.isdir(cfg_dir):
        for name in CONFIG_LAYERS:
            layer_path = os.path.join(cfg_dir, name)
            if os.path.exists(layer_path):
                _deep_merge(cfg, _read_yaml_file(layer_path))
    raw_root = _read_yaml_file(root_path)
    _deep_merge(cfg, raw_root)
    return cfg, raw_root


_CONFIG_CACHE = {}


def load_cfg(path: str = None, force_reload: bool = False) -> ConfigDict:
    """load_cfg function."""
    if path is None:
        path = get_path("cfg.yaml")

    abs_path = os.path.abspath(path)

    global _CONFIG_CACHE
    import sys
    is_testing = "pytest" in sys.modules or "unittest" in sys.modules

    if not force_reload and not is_testing and abs_path in _CONFIG_CACHE:
        import copy
        return copy.deepcopy(_CONFIG_CACHE[abs_path])

    if not os.path.exists(abs_path):
        raise FileNotFoundError(f"Configuration file not found: {abs_path}")

    cfg, raw_root = _load_layered_cfg(abs_path)

    if not cfg:
        raise ValueError(f"Configuration file is empty or invalid: {abs_path}")

    # Ensure required sections exist with at least empty dicts
    for key, default in default_structure.items():
        if key not in cfg:
            cfg[key] = default.copy() if isinstance(default, dict) else {}

    cfg.setdefault("agent", {})
    cfg["agent"]["workspace"] = resolve_local_path(
        cfg["agent"].get("workspace"), DEFAULT_WORKSPACE
    )

    # Set default audit_dir if not specified
    logging_cfg = cfg.setdefault("logging", {})
    if not logging_cfg.get("audit_dir"):
        logging_cfg["audit_dir"] = os.path.join(cfg["agent"]["workspace"], "logs")
    if logging_cfg.get("file"):
        logging_cfg["file"] = resolve_local_path(logging_cfg["file"])

    # Resolve sqlite db and audit dir relative to repo root.
    mem_cfg = cfg.setdefault("memory", {})
    if mem_cfg.get("sqlite_db_path"):
        mem_cfg["sqlite_db_path"] = resolve_local_path(mem_cfg.get("sqlite_db_path"))

    if logging_cfg.get("audit_dir"):
        logging_cfg["audit_dir"] = resolve_local_path(logging_cfg.get("audit_dir"))

    sec_cfg = cfg.setdefault("security", {})
    if sec_cfg.get("internal_data_dir"):
        sec_cfg["internal_data_dir"] = resolve_local_path(
            sec_cfg.get("internal_data_dir")
        )

    # Optional "power mode": relaxes most safety checks for local sandbox usage.
    # This does NOT implement privilege escalation, persistence, or stealth behaviors.
    autonomy_cfg = cfg.setdefault("autonomy", {})
    if autonomy_cfg.get("power_mode", False):
        rules = cfg.setdefault("rules", {})
        security = cfg.setdefault("security", {})

        # Explicitly open up high-risk capabilities.
        rules["allow_system_changes"] = True
        rules["allow_registry_edit"] = True
        rules["allow_service_control"] = True

        # Remove command validation blocks (user accepts risk).
        security["validate_commands"] = False

        # Reduce prompts/interaction for destructive steps.
        rules["require_confirm_destructive"] = False
        cfg.setdefault("agent", {})["auto_confirm"] = True
        autonomy_cfg.setdefault("autopilot", True)
        autonomy_cfg.setdefault("minimal_clarifications", True)
        autonomy_cfg.setdefault("enforce_progress", True)

    # Defensive normalization for common numeric fields (avoid invalid API parameters).
    try:
        nvidia_cfg = cfg.get("cloud", {}).get("nvidia", {}) or {}
        if "max_tokens" in nvidia_cfg and nvidia_cfg["max_tokens"] is not None:
            nvidia_cfg["max_tokens"] = int(nvidia_cfg["max_tokens"])
        if "timeout" in nvidia_cfg and nvidia_cfg["timeout"] is not None:
            nvidia_cfg["timeout"] = int(nvidia_cfg["timeout"])
    except (ValueError, TypeError) as e:
        import warnings

        warnings.warn(f"Invalid numeric value in cloud.nvidia cfg: {e}")

    # ── Startup cfg validation ────────────────────────────────────────────
    # Run after all merges/normalisation so the validator sees the final state.
    # Import lazily to avoid circular imports at module load time.
    try:
        from kernel.lint import warn_cfg_issues  # noqa: PLC0415
        warn_cfg_issues(cfg, root_cfg=raw_root)
    except Exception:
        pass  # Validator must never crash the agent

    # Validate configuration using Pydantic models
    try:
        from kernel.schema import ConfigDict as PydanticConfig
        PydanticConfig.model_validate(cfg)
    except Exception as e:
        import warnings
        warnings.warn(f"Pydantic configuration validation warning: {e}")

    _CONFIG_CACHE[abs_path] = cfg
    import copy
    return copy.deepcopy(cfg)
