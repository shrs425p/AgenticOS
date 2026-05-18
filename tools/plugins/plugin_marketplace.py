"""Plugin marketplace for AgenticOs.

Fetches a community plugin index from a configured GitHub repository and allows
installing plugins with a single command.

Config (config.yaml)::

    plugin_marketplace:
      index_url: "https://raw.githubusercontent.com/shrs425p/AgenticOS/main/docs/plugin_index.json"
"""

import json
import os
from pathlib import Path

from core.tool_registry import tool

_PLUGINS_DIR = Path("tools/plugins")

# Default community index URL (can be overridden in config.yaml)
_DEFAULT_INDEX_URL = (
    "https://raw.githubusercontent.com/shrs425p/AgenticOS/main/docs/plugin_index.json"
)


def _get_index_url() -> str:
    try:
        from core.runtime_config import load_config

        cfg = load_config()
        return cfg.get("plugin_marketplace", {}).get("index_url", _DEFAULT_INDEX_URL)
    except Exception:
        return _DEFAULT_INDEX_URL


@tool(
    name="list_marketplace_plugins",
    desc="Fetch and list available plugins from the community marketplace.",
    category="meta",
    version="1.0.0",
)
def list_marketplace_plugins() -> str:
    """Fetch the plugin index from the configured marketplace URL and return a summary.

    Returns:
        Formatted list of available plugins with name, description, and author.
    """
    try:
        import requests

        url = _get_index_url()
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        index = resp.json()
    except Exception as exc:
        return f"Error fetching marketplace index: {exc}"

    plugins = index.get("plugins", [])
    if not plugins:
        return "No plugins found in the marketplace index."

    lines = [f"# Community Plugin Marketplace ({len(plugins)} plugins)\n"]
    for p in plugins:
        name = p.get("name", "?")
        desc = p.get("description", "")
        author = p.get("author", "")
        version = p.get("version", "")
        installed = (_PLUGINS_DIR / f"{name}.py").exists()
        status = " [INSTALLED]" if installed else ""
        lines.append(f"• **{name}** v{version} by {author}{status}")
        lines.append(f"  {desc}")
    return "\n".join(lines)


@tool(
    name="install_marketplace_plugin",
    desc="Download and install a plugin from the community marketplace. Args: plugin_name (string).",
    category="meta",
    version="1.0.0",
)
def install_marketplace_plugin(plugin_name: str) -> str:
    """Download and install a plugin from the marketplace.

    Args:
        plugin_name: The plugin name (without .py extension).

    Returns:
        Status message indicating success or failure.
    """
    if not plugin_name or not plugin_name.isidentifier():
        return f"Error: '{plugin_name}' is not a valid plugin name."

    try:
        import requests

        url = _get_index_url()
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        index = resp.json()
    except Exception as exc:
        return f"Error fetching marketplace index: {exc}"

    plugins = {p.get("name"): p for p in index.get("plugins", [])}
    if plugin_name not in plugins:
        return (
            f"Plugin '{plugin_name}' not found in marketplace. "
            f"Available: {', '.join(sorted(plugins.keys()))}"
        )

    plugin_info = plugins[plugin_name]
    code_url = plugin_info.get("url")
    if not code_url:
        return f"No download URL for plugin '{plugin_name}'."

    dest_path = _PLUGINS_DIR / f"{plugin_name}.py"
    if dest_path.exists():
        return (
            f"Plugin '{plugin_name}' is already installed at {dest_path}. "
            "Remove it first if you want to reinstall."
        )

    try:
        import requests

        code_resp = requests.get(code_url, timeout=30)
        code_resp.raise_for_status()
        code = code_resp.text
    except Exception as exc:
        return f"Error downloading plugin '{plugin_name}': {exc}"

    # Basic security check: must use @tool decorator
    if "@tool" not in code:
        return (
            f"Security check failed: plugin '{plugin_name}' does not use the @tool decorator. "
            "Installation aborted."
        )

    try:
        _PLUGINS_DIR.mkdir(parents=True, exist_ok=True)
        dest_path.write_text(code, encoding="utf-8")
    except Exception as exc:
        return f"Error writing plugin file: {exc}"

    return (
        f"Plugin '{plugin_name}' installed successfully at {dest_path}.\n"
        "The hot-reloader will register it within a few seconds."
    )


@tool(
    name="preview_marketplace_plugin",
    desc="Preview the source code of a marketplace plugin before installing. Args: plugin_name.",
    category="meta",
    version="1.0.0",
)
def preview_marketplace_plugin(plugin_name: str) -> str:
    """Preview a marketplace plugin's source code.

    Args:
        plugin_name: The plugin name (without .py extension).

    Returns:
        First 2000 characters of the plugin source code.
    """
    try:
        import requests

        url = _get_index_url()
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        index = resp.json()
    except Exception as exc:
        return f"Error fetching marketplace index: {exc}"

    plugins = {p.get("name"): p for p in index.get("plugins", [])}
    if plugin_name not in plugins:
        return f"Plugin '{plugin_name}' not found in marketplace."

    code_url = plugins[plugin_name].get("url")
    if not code_url:
        return f"No download URL for plugin '{plugin_name}'."

    try:
        import requests

        code_resp = requests.get(code_url, timeout=30)
        code_resp.raise_for_status()
        code = code_resp.text
    except Exception as exc:
        return f"Error fetching plugin source: {exc}"

    preview = code[:2000]
    if len(code) > 2000:
        preview += "\n... (truncated)"
    return f"# Plugin: {plugin_name}\n\n```python\n{preview}\n```"
