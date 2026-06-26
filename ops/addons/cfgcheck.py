"""Module for validate_cfg_tool.py"""
import yaml
import datetime
import logging
from pathlib import Path
from kernel.registry import tool

logger = logging.getLogger(__name__)

def deep_merge(source, destination):
    """Deep merges source dict into destination dict."""
    for key, value in source.items():
        if isinstance(value, dict):
            # get node or create one
            node = destination.setdefault(key, {})
            deep_merge(value, node)
        else:
            destination[key] = value
    return destination

@tool(category="System", desc="Validates the AgenticOs configuration and generates an audit report")
def validate_cfg() -> str:
    """Reads cfg.yaml and layered files in cfg/, validates specific fields and their types,
    checks if the workspace is writable, and generates an audit report in workspace/daily_logs/."""

    root_dir = Path(".")
    cfg_yaml_path = root_dir / "cfg.yaml"
    cfg_dir = root_dir / "cfg"

    if not cfg_yaml_path.exists():
        return "Error: cfg.yaml is missing."

    merged_cfg = {}

    # Read cfg/ layered files first
    if cfg_dir.exists() and cfg_dir.is_dir():
        for yaml_file in sorted(cfg_dir.glob("*.yaml")):
            try:
                with open(yaml_file, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    if data and isinstance(data, dict):
                        deep_merge(data, merged_cfg)
            except Exception as e:
                logger.warning(f"Failed to read {yaml_file}: {e}")

    # Read root cfg.yaml (overrides)
    try:
        with open(cfg_yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            if data and isinstance(data, dict):
                deep_merge(data, merged_cfg)
    except Exception as e:
        return f"Error reading cfg.yaml: {e}"

    validation_results = {}

    # Helper to get nested keys
    def get_nested(cfg, keys_str):
        """get_nested function."""
        keys = keys_str.split('.')
        current = cfg
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        return current

    # Validation Rules
    # agent.provider
    provider = get_nested(merged_cfg, "agent.provider")
    if provider is None:
        validation_results["agent.provider"] = "missing"
    elif not isinstance(provider, str) or provider not in (["ollama"] + list(merged_cfg.get("cloud", {}).keys())):
        validation_results["agent.provider"] = "invalid_value"
    else:
        validation_results["agent.provider"] = "ok"

    # agent.workspace
    workspace = get_nested(merged_cfg, "agent.workspace")
    if workspace is None:
        validation_results["agent.workspace"] = "missing"
    else:
        # Check writable
        try:
            ws_path = Path(workspace)
            ws_path.mkdir(parents=True, exist_ok=True)
            test_file = ws_path / ".test_write"
            test_file.touch()
            test_file.unlink()
            validation_results["agent.workspace"] = "ok"
        except Exception:
            validation_results["agent.workspace"] = "not_writable"

    # autonomy.autopilot
    autopilot = get_nested(merged_cfg, "autonomy.autopilot")
    if autopilot is None:
        validation_results["autonomy.autopilot"] = "missing"
    elif not isinstance(autopilot, bool):
        validation_results["autonomy.autopilot"] = "wrong_type"
    else:
        validation_results["autonomy.autopilot"] = "ok"

    # provider specific models
    if provider == "nvidia":
        model = get_nested(merged_cfg, "cloud.nvidia.model")
        if model is None:
            validation_results["cloud.nvidia.model"] = "missing"
        else:
            validation_results["cloud.nvidia.model"] = "ok"
    elif provider == "gemini":
        model = get_nested(merged_cfg, "cloud.gemini.model")
        if model is None:
            validation_results["cloud.gemini.model"] = "missing"
        else:
            validation_results["cloud.gemini.model"] = "ok"

    # agent.stream type
    stream = get_nested(merged_cfg, "agent.stream")
    if stream is not None:
        if not isinstance(stream, bool):
            validation_results["agent.stream"] = "wrong_type"
        else:
            validation_results["agent.stream"] = "ok"

    # Write audit report
    today = datetime.date.today().isoformat()
    logs_dir = Path(workspace or "workspace") / "daily_logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    out_file = logs_dir / f"cfg_audit_{today}.md"

    report = [
        f"# Config Audit Report for {today}",
        "",
        "| Field | Status |",
        "|---|---|",
    ]

    for field, status in validation_results.items():
        report.append(f"| {field} | {status} |")

    try:
        with open(out_file, "w", encoding="utf-8") as f:
            f.write("\n".join(report))
    except Exception as e:
        logger.warning(f"Failed to write cfg audit report: {e}")

    return validation_results

if __name__ == "__main__":
    print(validate_cfg())
