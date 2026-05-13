"""Shared HTTP session helpers for WebTools."""

from __future__ import annotations


def requests_module():
    import requests

    return requests


def bs4_beautifulsoup():
    try:
        from bs4 import BeautifulSoup

        return BeautifulSoup
    except ImportError:
        return None


def build_default_session(existing_session=None):
    r = requests_module()
    sess = existing_session or r.Session()
    sess.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,"
                "image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7"
            ),
            "Referer": "https://duckduckgo.com/",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
        }
    )
    return sess


def parse_headers_json(headers: str) -> dict:
    if not headers:
        return {}
    try:
        import json

        parsed = json.loads(headers)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass
    return {}
