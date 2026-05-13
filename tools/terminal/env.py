from __future__ import annotations

import os


class EnvMixin:
    def get_env(self, name: str) -> str:
        return os.environ.get(name, "")

    def set_env(self, name: str, value: str) -> str:
        self._env_overrides[name] = value
        return f"Set {name}"

    def list_env(self, filter_str: str = "") -> str:
        flt = (filter_str or "").lower().strip()
        pairs = []
        for k, v in sorted(os.environ.items()):
            if flt and flt not in k.lower():
                continue
            pairs.append(f"{k}={v}")
        return "\n".join(pairs[:300]) if pairs else "(none)"

    def unset_env(self, name: str) -> str:
        self._env_overrides.pop(name, None)
        return f"Unset {name}"
