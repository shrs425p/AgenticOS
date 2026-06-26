"""Utility helpers for WebTools."""

from __future__ import annotations

from ops.web.session import bs4_beautifulsoup, requests_module


from kernel.base import tool
class UtilsMixin:
    @tool(name="shortenurl", desc="Shorten a URL. Args: url", category="Web")
    def shortenurl(self, url: str) -> str:
        """shortenurl function."""
        err = self._network_error()
        if err:
            return err
        try:
            r = requests_module()
            timeout = self._get_timeout("web_utils", 15)
            api = self.cfg.get("endpoints", {}).get("is_gd_api", "https://is.gd/create.php")
            resp = r.get(
                api,
                params={"format": "simple", "url": url},
                timeout=timeout,
            )
            return resp.text.strip()
        except Exception as e:
            return f"Shorten error: {e}"

    @tool(name="expandurl", desc="Follow redirects to final URL. Args: url", category="Web")
    def expandurl(self, url: str) -> str:
        """expandurl function."""
        err = self._network_error()
        if err:
            return err
        try:
            r = requests_module()
            timeout = self._get_timeout("web_utils", 15)
            resp = r.head(url, allow_redirects=True, timeout=timeout)
            return resp.url
        except Exception as e:
            return f"Expand error: {e}"

    @tool(name="rssfeed", desc="Fetch and parse RSS feed. Args: url, num_items (optional)", category="Web")
    def rssfeed(self, url: str, num_items: str = "5") -> str:
        """rssfeed function."""
        err = self._network_error()
        if err:
            return err
        try:
            n = min(int(num_items), 50)
            r = requests_module()
            timeout = self._get_timeout("web_utils", 20)
            resp = r.get(url, timeout=timeout)
            BS = bs4_beautifulsoup()
            if not BS:
                return (
                    "Install beautifulsoup4 for RSS parsing: pip install beautifulsoup4"
                )
            soup = BS(resp.text, "xml")
            items = []
            for item in soup.find_all("item")[:n]:
                title = (
                    item.find("title").get_text(strip=True)
                    if item.find("title")
                    else ""
                ).strip()
                link = (
                    item.find("link").get_text(strip=True) if item.find("link") else ""
                ).strip()
                pub = (
                    item.find("pubDate").get_text(strip=True)
                    if item.find("pubDate")
                    else ""
                ).strip()
                parts = [p for p in (title, link, pub) if p]
                if parts:
                    items.append(" | ".join(parts))
            return "\n".join(items) if items else "No RSS items found."
        except Exception as e:
            return f"RSS error: {e}"

    @tool(name="waybacksnapshot", desc="Get Wayback Machine snapshot. Args: url", category="Web")
    def waybacksnapshot(self, url: str) -> str:
        """waybacksnapshot function."""
        err = self._network_error()
        if err:
            return err
        try:
            r = requests_module()
            timeout = self._get_timeout("web_utils", 20)
            api = self.cfg.get("endpoints", {}).get("wayback_api", "https://archive.org/wayback/available")
            resp = r.get(api, params={"url": url}, timeout=timeout)
            return resp.text
        except Exception as e:
            return f"Wayback error: {e}"

    @tool(name="scrapetable", desc="Scrape HTML table. Args: url, table_index (optional)", category="Web")
    def scrapetable(self, url: str, table_index: str = "0") -> str:
        """scrapetable function."""
        err = self._network_error()
        if err:
            return err
        try:
            idx = int(table_index)
            sess = self._get_session()
            timeout = self._get_timeout("web_utils", 20)
            resp = sess.get(url, timeout=timeout)
            if resp.status_code != 200:
                return f"Error: status {resp.status_code}"

            BS = bs4_beautifulsoup()
            if not BS:
                return "Install beautifulsoup4 for HTML parsing: pip install beautifulsoup4"
            soup = BS(resp.text, "html.parser")
            tables = soup.find_all("table")
            if not tables:
                return "No tables found."
            if idx < 0 or idx >= len(tables):
                return f"Table index out of range. Found {len(tables)} tables."

            rows = []
            for tr in tables[idx].find_all("tr"):
                cols = [c.get_text(" ", strip=True) for c in tr.find_all(["th", "td"])]
                if cols:
                    rows.append(cols)
            if not rows:
                return "Table had no rows."
            return "\n".join(" | ".join(r) for r in rows[:200])
        except Exception as e:
            return f"Table scrape error: {e}"
