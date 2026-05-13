from __future__ import annotations

import re
import urllib.parse

from tools.web.session import requests_module


class YouTubeMixin:
    def find_youtube_video(self, query: str, channel: str = "") -> str:
        """Best-effort: find a YouTube watch URL for a query.

        Returns a single URL string on success, otherwise an error message.
        """
        q = (query or "").strip()
        c = (channel or "").strip()
        if not q:
            return "Error: query required."

        full_query = f"{q} {c} site:youtube.com watch".strip()
        try:
            r = requests_module()
            dq = urllib.parse.quote_plus(full_query)
            url = f"https://api.duckduckgo.com/?q={dq}&format=json&no_redirect=1&no_html=1"
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
