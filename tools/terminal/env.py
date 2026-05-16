"""Module for env.py"""
from __future__ import annotations

import os


from core.tool_base import tool
class EnvMixin:
    @tool(name="get_env", desc="Get env variable. Args: name", category="Terminal")
    def get_env(self, name: str) -> str:
        return os.environ.get(name, "")

    @tool(name="set_env", desc="Set env variable (session). Args: name, value", category="Terminal")
    def set_env(self, name: str, value: str) -> str:
        self._env_overrides[name] = value
        return f"Set {name}"

    @tool(name="list_env", desc="List env variables. Args: filter_str (optional)", category="Terminal")
    def list_env(self, filter_str: str = "") -> str:
        flt = (filter_str or "").lower().strip()
        pairs = []
        for k, v in sorted(os.environ.items()):
            if flt and flt not in k.lower():
                continue
            pairs.append(f"{k}={v}")
        return "\n".join(pairs[:300]) if pairs else "(none)"

    @tool(name="unset_env", desc="Unset env variable. Args: name", category="Terminal")
    def unset_env(self, name: str) -> str:
        self._env_overrides.pop(name, None)
        return f"Unset {name}"
