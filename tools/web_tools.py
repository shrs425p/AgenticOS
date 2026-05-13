"""
AgenticOs — web tools
Web tools: search, fetch, download, API calls, scraping, headers, whois, DNS, and utilities.
"""

from __future__ import annotations

from pathlib import Path

from tools.web.api import ApiMixin
from tools.web.browser import BrowserMixin
from tools.web.fetch import FetchMixin
from tools.web.inspect import InspectMixin
from tools.web.search import SearchMixin
from tools.web.session import build_default_session
from tools.web.spotify import SpotifyMixin
from tools.web.youtube import YouTubeMixin
from tools.web.utils import UtilsMixin
from tools.terminal.openers import OpenersMixin


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
        from tools.web.browser import BrowserManager

        self.browser_mgr = BrowserManager()

    def _get_timeout(self, key: str, default: int) -> int:
        """Get timeout from config or use default."""
        return self.cfg.get("timeouts", {}).get(key, default)

    def _get_session(self):
        if self._session is None:
            self._session = build_default_session()
        return self._session

    def _resolve_path_in_base(self, path: str) -> Path:
        p = Path(path)
        if not p.is_absolute():
            return (self.base_dir / p).resolve()
        resolved = p.resolve()
        base = self.base_dir.resolve()
        if str(resolved).lower().startswith(str(base).lower()):
            return resolved
        return (base / resolved.name).resolve()
