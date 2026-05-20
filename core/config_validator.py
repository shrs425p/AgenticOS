"""Startup config validator for AgenticOs.

Validates the fully-merged config dict (root config.yaml + config/*.yaml layers)
and emits structured warnings for missing or clearly invalid keys.

Design goals
------------
* Never crash the agent — all findings are warnings, not exceptions.
* Be layered-config-aware: only flag keys that are absent *after* all layers
  have been merged, so users aren't penalised for relying on defaults.
* Surface actionable hints, not raw key paths.
"""

from __future__ import annotations





import os
from dataclasses import dataclass, field
from typing import Any, List, Optional
from core.logger import get_logger
logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Provider → expected env-var mappings.
# These are the *minimum* keys a user must supply to connect to each cloud.
# ---------------------------------------------------------------------------

_PROVIDER_ENV_KEYS: dict[str, str] = {
    "nvidia":     "NVIDIA_API_KEY",
    "gemini":     "GEMINI_API_KEY",
    "groq":       "GROQ_API_KEY",
    "openai":     "OPENAI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "github":     "GITHUB_TOKEN",
    "deepseek":   "DEEPSEEK_API_KEY",
}

_KNOWN_PROVIDERS = {"ollama", *_PROVIDER_ENV_KEYS.keys()}

# Keys recognised at the *root* of config.yaml that override layered values.
# Any key in the user's root file that isn't in this set gets a typo warning.
_KNOWN_ROOT_KEYS = {
    "log_level",
    "agent", "cloud", "autonomy", "ollama", "memory", "cache",
    "logging", "rules", "security", "performance", "heuristics",
    "prompts", "policy", "tools", "terminal", "browser", "media",
    "parser", "hot_reload", "windows_paths", "timeouts", "endpoints",
    "rate_limits", "custom_keys",
}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ConfigIssue:
    level: str          # "ERROR" | "WARNING" | "INFO"
    message: str
    hint: Optional[str] = None

    def __str__(self) -> str:
        base = f"[{self.level}] {self.message}"
        if self.hint:
            base += f"\n         Hint: {self.hint}"
        return base


@dataclass
class ValidationResult:
    issues: List[ConfigIssue] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        """has_errors function."""
        return any(i.level == "ERROR" for i in self.issues)

    @property
    def has_warnings(self) -> bool:
        """has_warnings function."""
        return any(i.level in ("ERROR", "WARNING") for i in self.issues)

    def add(self, level: str, message: str, hint: str = "") -> None:
        """add function."""
        self.issues.append(ConfigIssue(level, message, hint or None))


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get(cfg: dict, *keys: str, default: Any = None) -> Any:
    """Safe nested get."""
    node: Any = cfg
    for k in keys:
        if not isinstance(node, dict):
            return default
        node = node.get(k, default)
        if node is None:
            return default
    return node


def _env_set(var: str) -> bool:
    """Return True if the env var is set and non-empty."""
    val = os.environ.get(var, "").strip()
    return bool(val) and val.lower() not in ("none", "null", "")


# ---------------------------------------------------------------------------
# Individual check functions
# ---------------------------------------------------------------------------

def _check_agent_section(cfg: dict, result: ValidationResult) -> None:
    agent = cfg.get("agent", {})

    # --- provider ---
    provider = (agent.get("provider") or "").strip().lower()
    if not provider:
        result.add(
            "WARNING",
            "agent.provider is not set.",
            "Add 'agent:\\n  provider: ollama' (or nvidia/gemini/…) to config.yaml.",
        )
    elif provider not in _KNOWN_PROVIDERS:
        result.add(
            "WARNING",
            f"agent.provider '{provider}' is not a recognised value.",
            f"Known providers: {', '.join(sorted(_KNOWN_PROVIDERS))}. "
            "Check for typos in config.yaml.",
        )

    # --- cloud-provider API key ---
    if provider in _PROVIDER_ENV_KEYS:
        env_var = _PROVIDER_ENV_KEYS[provider]
        if not _env_set(env_var):
            result.add(
                "WARNING",
                f"agent.provider is '{provider}' but {env_var} is not"
                " set in the environment.",
                f"Set {env_var} in your .env file or shell before starting the agent.",
            )
        # Also check that the relevant cloud.<provider>.model is non-empty
        model = _get(cfg, "cloud", provider, "model")
        if not model:
            result.add(
                "WARNING",
                f"cloud.{provider}.model is missing.",
                f"Add a model under 'cloud:\\n  {provider}:\\n    model: <name>' "
                f"in config/{provider}.yaml or config/providers.yaml.",
            )

    # --- max_iterations ---
    max_iter = agent.get("max_iterations")
    if max_iter is not None:
        try:
            if int(max_iter) < 1:
                raise ValueError
        except (ValueError, TypeError):
            result.add(
                "WARNING",
                f"agent.max_iterations must be a positive integer (got: {max_iter!r}).",
                "Set it to at least 1 (e.g. max_iterations: 100).",
            )

    # --- workspace ---
    workspace = agent.get("workspace", "")
    if workspace:
        if not os.path.isabs(workspace):
            # Relative paths are fine — just note them
            pass
        elif not os.path.exists(workspace):
            # Try to see if the parent exists (we create it at runtime, but warn early)
            parent = os.path.dirname(workspace)
            if not os.path.exists(parent):
                result.add(
                    "WARNING",
                    f"agent.workspace parent directory does not exist: {parent}",
                    "The agent will attempt to create it, but verify"
                    " the path is correct.",
                )


def _check_memory_section(cfg: dict, result: ValidationResult) -> None:
    memory = cfg.get("memory", {})
    backend = (memory.get("backend") or "sqlite").strip().lower()
    known_backends = {"sqlite", "json", "in_memory", "in-memory"}
    if backend not in known_backends:
        result.add(
            "WARNING",
            f"memory.backend '{backend}' is not a recognised value.",
            f"Known backends: {', '.join(sorted(known_backends))}.",
        )


def _check_security_section(cfg: dict, result: ValidationResult) -> None:
    security = cfg.get("security", {})
    sandbox = security.get("sandbox_mode", False)
    power_mode = _get(cfg, "autonomy", "power_mode", default=False)

    if sandbox and power_mode:
        result.add(
            "WARNING",
            "security.sandbox_mode is true but autonomy.power_mode is also true.",
            "power_mode overrides several sandbox restrictions. "
            "Disable one of them to avoid unexpected behaviour.",
        )


def _check_logging_section(cfg: dict, result: ValidationResult) -> None:
    logging_cfg = cfg.get("logging", {})
    level = (logging_cfg.get("level") or "").strip().upper()
    known_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL", ""}
    if level and level not in known_levels:
        result.add(
            "WARNING",
            f"logging.level '{level}' is not a standard Python log level.",
            f"Use one of: {', '.join(sorted(known_levels) - {''})}.",
        )

    audit_fmt = (logging_cfg.get("audit_format") or "").strip().lower()
    if audit_fmt and audit_fmt not in {"jsonl", "json", "both", "text", ""}:
        result.add(
            "WARNING",
            f"logging.audit_format '{audit_fmt}' is not a recognised value.",
            "Use 'jsonl', 'json', 'both', or 'text'.",
        )


def _check_heuristics_section(cfg: dict, result: ValidationResult) -> None:
    heuristics = cfg.get("heuristics", {})

    for int_key in (
        "dream_interval_hours",
        "slow_task_threshold_seconds",
        "dream_task_limit",
        "prose_vs_tool_threshold",
        "max_dots_in_response",
        "iteration_warning_threshold",
        "new_task_min_chars",
        "direct_response_max_chars",
        "direct_response_max_words",
    ):
        val = heuristics.get(int_key)
        if val is not None:
            try:
                if int(val) < 0:
                    raise ValueError
            except (ValueError, TypeError):
                result.add(
                    "WARNING",
                    f"heuristics.{int_key} should be a non-negative"
                    f" integer (got: {val!r}).",
                )

    throttle = heuristics.get("hot_reload_throttle")
    if throttle is not None:
        try:
            if float(throttle) < 0:
                raise ValueError
        except (ValueError, TypeError):
            result.add(
                "WARNING",
                f"heuristics.hot_reload_throttle should be a non-negative number "
                f"(got: {throttle!r}).",
            )


def _check_unknown_root_keys(root_cfg: dict, result: ValidationResult) -> None:
    """Warn about keys in the *root* config.yaml that aren't recognised.

    This helps catch typos like ``agnet:`` or ``automony:``.
    We receive the root file's raw dict separately from the merged config
    so we only flag keys the user explicitly wrote, not defaults.
    """
    if not isinstance(root_cfg, dict):
        return
    unknown = set(root_cfg.keys()) - _KNOWN_ROOT_KEYS
    for key in sorted(unknown):
        result.add(
            "WARNING",
            f"Unrecognised top-level key '{key}' in config.yaml.",
            f"Did you mean one of: {', '.join(sorted(_KNOWN_ROOT_KEYS))}? "
            "Unknown keys are silently ignored.",
        )


def _check_ollama_section(cfg: dict, result: ValidationResult) -> None:
    provider = _get(cfg, "agent", "provider", default="").lower()
    if provider != "ollama":
        return  # only relevant for Ollama users

    ollama = cfg.get("ollama", {})
    base_url = (ollama.get("base_url") or "").strip()
    if not base_url:
        result.add(
            "WARNING",
            "agent.provider is 'ollama' but ollama.base_url is not set.",
            "Add 'ollama:\\n  base_url: http://localhost:11434' "
            "to config/providers.yaml (or config.yaml).",
        )

    model = ollama.get("default_model") or ""
    if not model:
        result.add(
            "INFO",
            "ollama.default_model is not set — the agent will prompt"
            " you to choose a model.",
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_config(
    merged_cfg: dict,
    *,
    root_cfg: Optional[dict] = None,
) -> ValidationResult:
    """Run all checks against the fully-merged config.

    Parameters
    ----------
    merged_cfg:
        The dict returned by ``load_config()`` after all layer merges.
    root_cfg:
        (Optional) The raw dict loaded *only* from the root ``config.yaml``
        before merging.  When supplied, unknown-key detection is enabled.

    Returns
    -------
    ValidationResult
        Contains a list of :class:`ConfigIssue` instances.
    """
    result = ValidationResult()

    _check_agent_section(merged_cfg, result)
    _check_ollama_section(merged_cfg, result)
    _check_memory_section(merged_cfg, result)
    _check_security_section(merged_cfg, result)
    _check_logging_section(merged_cfg, result)
    _check_heuristics_section(merged_cfg, result)

    if root_cfg is not None:
        _check_unknown_root_keys(root_cfg, result)

    return result


def warn_config_issues(
    merged_cfg: dict,
    *,
    root_cfg: Optional[dict] = None,
    quiet: bool = False,
) -> ValidationResult:
    """Validate and print warnings to stdout.

    Call this once at startup.  Tries to use AgenticOs's own print helpers
    so the output blends in with the banner; falls back to plain ``print``
    if the UI module isn't available yet.

    Parameters
    ----------
    quiet:
        If ``True``, suppress INFO-level issues (only show WARNING / ERROR).
    """
    result = validate_config(merged_cfg, root_cfg=root_cfg)
    if not result.issues:
        return result

    try:
        from core.runtime_ui import print_warning, print_error, print_info  # noqa: PLC0415
        _warn = print_warning
        _err  = print_error
        _info = print_info
    except Exception:
        def _warn(msg: str) -> None:  # type: ignore[misc]
            logger.info(f"  ▲  {msg}")

        def _err(msg: str) -> None:  # type: ignore[misc]
            logger.info(f"  ✗  {msg}")

        def _info(msg: str) -> None:  # type: ignore[misc]
            logger.info(f"  ◆  {msg}")

    printed_header = False
    for issue in result.issues:
        if quiet and issue.level == "INFO":
            continue
        if not printed_header:
            logger.info("  ── Config Validation ────────────────────────────────────")
            printed_header = True

        body = issue.message
        if issue.hint:
            body += f"\n         → {issue.hint}"

        if issue.level == "ERROR":
            _err(body)
        elif issue.level == "WARNING":
            _warn(body)
        else:
            _info(body)

    if printed_header:
        logger.info("  ─────────────────────────────────────────────────────────")

    return result
