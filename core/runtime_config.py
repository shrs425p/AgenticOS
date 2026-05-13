"""Config and path helpers for the AgenticOs runtime."""

import os

import yaml


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_path(rel_path: str) -> str:
    return os.path.join(BASE_DIR, rel_path)


def resolve_local_path(path: str, default: str = "") -> str:
    raw_path = path or default
    expanded = os.path.expandvars(os.path.expanduser(raw_path))
    if not os.path.isabs(expanded):
        expanded = os.path.join(BASE_DIR, expanded)
    return os.path.abspath(expanded)


DEFAULT_WORKSPACE = resolve_local_path(
    os.environ.get("AGENTICOS_WORKSPACE", "workspace")
)

# Minimal structure defaults - all actual values come from config.yaml
default_structure = {
    "ollama": {},
    "agent": {"workspace": DEFAULT_WORKSPACE},
    "autonomy": {},
    "cloud": {"nvidia": {}},
    "memory": {},
    "rules": {},
    "security": {},
    "logging": {},
    "tools": {},
    "performance": {},
    "timeouts": {},
}


def load_config(path: str = None) -> dict:
    if path is None:
        path = get_path("config.yaml")

    if not os.path.exists(path):
        raise FileNotFoundError(f"Configuration file not found: {path}")

    with open(path, encoding="utf-8") as handle:
        cfg = yaml.safe_load(handle)

    if not cfg:
        raise ValueError(f"Configuration file is empty or invalid: {path}")

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

        warnings.warn(f"Invalid numeric value in cloud.nvidia config: {e}")

    return cfg
