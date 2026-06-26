"""
AgenticOs — web ops
Web ops: search, fetch, download, API calls, scraping, headers, whois, DNS, and utilities.
"""

from __future__ import annotations

from pathlib import Path

from ops.web.api import ApiMixin
from ops.web.browser import BrowserMixin
from ops.web.fetch import FetchMixin
from ops.web.inspect import InspectMixin
from ops.web.search import SearchMixin
from ops.web.session import build_default_session
from ops.web.spotify import SpotifyMixin
from ops.web.youtube import YouTubeMixin
from ops.web.utils import UtilsMixin
from ops.shell.open import OpenersMixin


class WebTools(
    SearchMixin,
    FetchMixin,
    ApiMixin,
    InspectMixin,
    UtilsMixin,
    SpotifyMixin,
    YouTubeMixin,
    BrowserMixin,
    OpenersMixin,
):
    def __init__(
        self,
        rules: dict | None = None,
        base_dir: str = "workspace",
        cfg: dict | None = None,
    ):
        self.rules = rules or {}
        self.cfg = cfg or {}
        self.base_dir = Path(base_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._session = None
        from ops.web.browser import BrowserManager

        self.browser_mgr = BrowserManager()

    def _get_timeout(self, key: str, default: int) -> int:
        """Get timeout from cfg or use default."""
        return self.cfg.get("timeouts", {}).get(key, default)

    def _get_endpoint(self, key: str, default: str) -> str:
        """Get endpoint from cfg or use default."""
        return self.cfg.get("web", {}).get("search_endpoints", {}).get(key, default)

    def _get_session(self):
        if self._session is None:
            self._session = build_default_session()
        return self._session

    def _network_error(self, capability: str = "network") -> str:
        if not self.rules.get("allow_network_access", True):
            return "Error: network access is disabled by cfg."
        if capability == "search" and not self.rules.get("allow_websearch", True):
            return "Error: web search is disabled by cfg."
        if capability == "download" and not self.rules.get("allow_web_download", True):
            return "Error: web download is disabled by cfg."
        return ""

    def _resolve_path_in_base(self, path: str) -> Path:
        p = Path(path)
        if not p.is_absolute():
            return (self.base_dir / p).resolve()
        resolved = p.resolve()
        base = self.base_dir.resolve()
        if str(resolved).lower().startswith(str(base).lower()):
            return resolved
        return (base / resolved.name).resolve()
