"""Search-related methods for WebTools."""

from __future__ import annotations

import time
import urllib.parse

from tools.web.session import bs4_beautifulsoup, requests_module


class SearchMixin:
    def search(self, query: str, num_results: str = "5") -> str:
        """Search the web using DuckDuckGo (no API key needed)."""
        err = self._network_error("search")
        if err:
            return err
        try:
            r = requests_module()
            n = min(int(num_results), 20)
            q = urllib.parse.quote_plus(query)
            url = (
                f"https://api.duckduckgo.com/?q={q}&format=json&no_redirect=1&no_html=1"
            )
            timeout = self._get_timeout("web_search", 15)
            resp = r.get(url, timeout=timeout)
            data = resp.json()

            results = []
            if data.get("AbstractText"):
                results.append(f"Summary: {data['AbstractText']}")
                if data.get("AbstractURL"):
                    results.append(f"Source: {data['AbstractURL']}")

            topics = data.get("RelatedTopics", [])
            for topic in topics[:n]:
                if isinstance(topic, dict) and topic.get("Text"):
                    results.append(f"\n- {topic['Text']}")
                    if topic.get("FirstURL"):
                        results.append(f"  URL: {topic['FirstURL']}")
                elif isinstance(topic, dict) and topic.get("Topics"):
                    for sub in topic["Topics"][:3]:
                        if sub.get("Text"):
                            results.append(f"\n- {sub['Text']}")
                            if sub.get("FirstURL"):
                                results.append(f"  URL: {sub['FirstURL']}")

            if data.get("Answer"):
                results.insert(0, f"Direct Answer: {data['Answer']}")

            if not results:
                ddg_res = self._ddg_html_search(query, n)
                if "Search error" in ddg_res or "No results found" in ddg_res:
                    return self._bing_fallback_search(query, n)
                return ddg_res

            return "\n".join(results)
        except Exception as e:
            return f"Search error: {e}"

    def _ddg_html_search(self, query: str, n: int = 5) -> str:
        """Fallback HTML scrape of DuckDuckGo."""
        err = self._network_error("search")
        if err:
            return err
        try:
            sess = self._get_session()
            q = urllib.parse.quote_plus(query)
            url = f"https://html.duckduckgo.com/html/?q={q}"
            max_retries = 3
            for attempt in range(max_retries):
                timeout = self._get_timeout("web_search", 15)
                resp = sess.get(url, timeout=timeout)
                if resp.status_code == 200:
                    break
                if resp.status_code == 202 and attempt < max_retries - 1:
                    time.sleep(2 * (attempt + 1))
                    continue
                return (
                    f"Search error: Received status {resp.status_code} from DuckDuckGo "
                    f"after {attempt + 1} attempts."
                )

            BS = bs4_beautifulsoup()
            if not BS:
                return "Install beautifulsoup4 for richer search results: pip install beautifulsoup4"

            soup = BS(resp.text, "html.parser")
            results = []

            items = soup.select(".result") or soup.select(".result__body")
            for result in items[:n]:
                title_a = result.select_one(".result__a") or result.select_one(
                    "a.result__title"
                )
                title = title_a.get_text(strip=True) if title_a else "No Title"
                link = title_a.get("href") if title_a else ""

                if link and link.startswith("//"):
                    link = "https:" + link
                if link and "uddg=" in link:
                    parsed = urllib.parse.urlparse(link)
                    qs = urllib.parse.parse_qs(parsed.query)
                    if "uddg" in qs:
                        link = qs["uddg"][0]

                snip_el = result.select_one(".result__snippet")
                snip = (
                    snip_el.get_text(strip=True) if snip_el else "No snippet available."
                )

                if title != "No Title":
                    results.append(f"- {title}\n  {link}\n  {snip}")

            return (
                "\n\n".join(results)
                if results
                else "No results found. (HTML structure might have changed)"
            )
        except Exception as e:
            return f"Fallback search error: {e}"

    def _bing_fallback_search(self, query: str, n: int = 5) -> str:
        """Fallback HTML scrape of Bing with curl-like headers."""
        err = self._network_error("search")
        if err:
            return err
        try:
            headers = {
                "User-Agent": "curl/8.16.0",
                "Accept": "*/*",
                "Accept-Language": "en-US,en;q=0.9",
            }
            q = urllib.parse.quote_plus(query)
            url = f"https://www.bing.com/search?q={q}"
            r = requests_module()
            timeout = self._get_timeout("web_search", 15)
            resp = r.get(url, headers=headers, timeout=timeout)
            if resp.status_code != 200:
                return f"Bing fallback error: Received status {resp.status_code}."

            BS = bs4_beautifulsoup()
            if not BS:
                return "Install beautifulsoup4 for richer search results: pip install beautifulsoup4"

            soup = BS(resp.text, "html.parser")
            results = []
            for item in soup.select(".b_algo")[:n]:
                title_el = item.find("h2")
                if not title_el:
                    continue
                a = title_el.find("a", href=True)
                if not a:
                    continue
                title = a.get_text(strip=True)
                link = a["href"]

                snippet_el = item.select_one(".b_caption p")
                snippet = snippet_el.get_text(strip=True) if snippet_el else ""
                results.append(f"- {title}\n  {link}\n  {snippet}")

            return "\n\n".join(results) if results else "No results found."
        except Exception as e:
            return f"Bing fallback search error: {e}"

    def search_news(self, query: str, num_results: str = "5") -> str:
        """Search news by scraping DuckDuckGo's news results (best effort)."""
        try:
            n = min(int(num_results), 20)
            sess = self._get_session()
            q = urllib.parse.quote_plus(query)
            url = f"https://duckduckgo.com/?q={q}&iar=news&ia=news"
            timeout = self._get_timeout("web_search", 15)
            resp = sess.get(url, timeout=timeout)

            BS = bs4_beautifulsoup()
            if not BS:
                return "Install beautifulsoup4 for richer news results: pip install beautifulsoup4"

            soup = BS(resp.text, "html.parser")
            results = []
            for a in soup.select("a.result__a")[:n]:
                title = a.get_text(strip=True)
                link = a.get("href", "")
                if title and link:
                    results.append(f"- {title}\n  {link}")
            return "\n\n".join(results) if results else "No news results found."
        except Exception as e:
            return f"News search error: {e}"
