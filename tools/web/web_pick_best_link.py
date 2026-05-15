"""Standalone web_pick_best_link helper.

This module is intentionally self-contained so it can be registered as a tool
without requiring changes to existing WebTools internals.
"""

from __future__ import annotations

import re
import urllib.parse

import requests
from core.runtime_config import load_config


def web_pick_best_link(query: str, domain_hint: str = "") -> str:
    """Search Google HTML results and pick a best link.

    Notes:
    - This is a best-effort helper for "open the actual thing" workflows.
    - It avoids requiring an API key by parsing the search results page.
    """
    q = (query or "").strip()
    if not q:
        return "Error: query required."
    hint = (domain_hint or "").strip().lower()

    cfg = load_config()
    base_url = cfg.get("endpoints", {}).get("google_search", "https://www.google.com/search?q=")
    url = base_url + urllib.parse.quote(q)
    headers = {
        "User-Agent": cfg.get("tools", {}).get("web", {}).get("user_agent", (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/123.0 Safari/537.36"
        ))
    }
    try:
        timeout = cfg.get("timeouts", {}).get("web_search", 20)
        r = requests.get(url, headers=headers, timeout=timeout)
        r.raise_for_status()
        html = r.text or ""
    except Exception as e:
        return f"Error: search failed: {type(e).__name__}: {e}"

    # Pull outbound URLs. Google encodes as /url?q=<target>&...
    candidates: list[str] = []
    for m in re.findall(r"/url\?q=(https?%3A%2F%2F[^&]+)", html):
        try:
            u = urllib.parse.unquote(m)
        except Exception:
            u = m
        if u.startswith("http"):
            candidates.append(u)

    # De-dupe while preserving order.
    seen = set()
    uniq = []
    for u in candidates:
        if u in seen:
            continue
        seen.add(u)
        uniq.append(u)

    if hint:
        for u in uniq:
            if hint in u.lower():
                return u
    if uniq:
        return uniq[0]
    return "Error: no link found."
