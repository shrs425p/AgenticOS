"""Module for youtube.py"""
from __future__ import annotations

import re
import urllib.parse

from tools.web.session import requests_module
from tools.web.browser import _ensure_browser, BrowserManager


from core.tool_base import tool
class YouTubeMixin:
    @tool(name="youtube_play_next", desc="Skip to the next YouTube video in the active browser tab.", category="Web")
    @_ensure_browser
    async def youtube_play_next(self, mgr: BrowserManager) -> str:
        """Skip to the next YouTube video.

        Requires an active browser session showing a YouTube page.
        """
        if mgr.page is None:
            return "Error: No browser session active."
        url = mgr.page.url or ""
        if "youtube.com" not in url:
            return "Error: Active browser tab is not on YouTube."

        try:
            if "watch" not in url:
                # If we are on search results, click the first video title instead
                first_video = "ytd-video-renderer a#video-title, a#video-title"
                await mgr.page.click(first_video, timeout=5000)
                return "Clicked first video in search results."

            # Click next button in player controls
            next_btn = "button.ytp-next-button, a.ytp-next-button"
            await mgr.page.click(next_btn, timeout=5000)
            return "Clicked next video button in player controls."
        except Exception as e:
            # Fallback to keypress
            try:
                await mgr.page.keyboard.press("Shift+N")
                return "Pressed Shift+N to play next video."
            except Exception as e2:
                return f"Error skipping video: {e} | {e2}"

    @tool(name="youtube_play_pause", desc="Toggle play/pause of the YouTube video in the active browser tab.", category="Web")
    @_ensure_browser
    async def youtube_play_pause(self, mgr: BrowserManager) -> str:
        """Toggle play/pause of the YouTube video."""
        if mgr.page is None:
            return "Error: No browser session active."
        url = mgr.page.url or ""
        if "youtube.com" not in url:
            return "Error: Active browser tab is not on YouTube."

        try:
            await mgr.page.keyboard.press("k")
            return "Toggled play/pause (pressed 'k')."
        except Exception as e:
            return f"Error toggling play/pause: {e}"

    @tool(name="youtube_skip_ad", desc="Skip any active advertisement playing on YouTube.", category="Web")
    @_ensure_browser
    async def youtube_skip_ad(self, mgr: BrowserManager) -> str:
        """Attempt to skip any playing advertisement."""
        if mgr.page is None:
            return "Error: No browser session active."
        url = mgr.page.url or ""
        if "youtube.com" not in url:
            return "Error: Active browser tab is not on YouTube."

        selectors = [
            "button.ytp-skip-ad-button",
            ".ytp-ad-skip-button",
            ".ytp-ad-skip-button-text",
            ".ytp-skip-ad-button-hover"
        ]
        try:
            for selector in selectors:
                try:
                    el = await mgr.page.query_selector(selector)
                    if el and await el.is_visible():
                        await el.click()
                        return f"Successfully clicked skip ad button: {selector}"
                except Exception:
                    pass
            return "No visible skip ad button detected."
        except Exception as e:
            return f"Error checking/skipping ad: {e}"

    @tool(name="find_youtube_video", desc="Find YouTube video link. Args: query, channel (optional)", category="Web")
    def find_youtube_video(self, query: str, channel: str = "") -> str:
        """Best-effort: find a YouTube watch URL for a query.

        Returns a single URL string on success, otherwise an error message.
        """
        err = self._network_error("search")
        if err:
            return err
        q = (query or "").strip()
        c = (channel or "").strip()
        if not q:
            return "Error: query required."

        full_query = f"{q} {c} site:youtube.com watch".strip()
        try:
            r = requests_module()
            dq = urllib.parse.quote_plus(full_query)
            api_base = self.cfg.get("endpoints", {}).get("duckduckgo_api", "https://api.duckduckgo.com")
            url = f"{api_base}/?q={dq}&format=json&no_redirect=1&no_html=1"
            timeout = self._get_timeout("web_search", 15)
            resp = r.get(url, timeout=timeout)
            data = resp.json() or {}

            candidates: list[str] = []
            topics = data.get("RelatedTopics", []) or []
            for topic in topics:
                if isinstance(topic, dict) and topic.get("FirstURL"):
                    candidates.append(topic["FirstURL"])
                if isinstance(topic, dict) and topic.get("Topics"):
                    for sub in topic["Topics"]:
                        if isinstance(sub, dict) and sub.get("FirstURL"):
                            candidates.append(sub["FirstURL"])

            blob = str(data)
            candidates.extend(
                re.findall(
                    r"https?://www\.youtube\.com/watch\?v=[A-Za-z0-9_-]{6,}", blob
                )
            )
            candidates.extend(
                re.findall(r"https?://youtube\.com/watch\?v=[A-Za-z0-9_-]{6,}", blob)
            )

            watch_urls = []
            for cnd in candidates:
                if not isinstance(cnd, str):
                    continue
                if "youtube.com/watch" in cnd and "v=" in cnd:
                    watch_urls.append(cnd.split("&")[0].split("?t=")[0])

            seen = set()
            uniq = []
            for u in watch_urls:
                if u not in seen:
                    seen.add(u)
                    uniq.append(u)

            if uniq:
                return uniq[0]
            return "Error: Could not find a YouTube video link."
        except Exception as e:
            return f"Error: {type(e).__name__}: {e}"
