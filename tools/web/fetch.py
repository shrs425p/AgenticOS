"""Fetch/scrape/download methods for WebTools."""

from __future__ import annotations

import urllib.parse

from tools.web.session import bs4_beautifulsoup, requests_module


class FetchMixin:
    def fetch_url(self, url: str, timeout: str = "15") -> str:
        try:
            r = requests_module()
            resp = r.get(url, timeout=int(timeout))
            return resp.text
        except Exception as e:
            return f"Fetch error: {e}"

    def get_page_text(self, url: str) -> str:
        try:
            sess = self._get_session()
            timeout = self._get_timeout("web_fetch", 15)
            resp = sess.get(url, timeout=timeout)
            if resp.status_code != 200:
                return f"Error: status {resp.status_code}"

            BS = bs4_beautifulsoup()
            if not BS:
                return "Install beautifulsoup4 for richer extraction: pip install beautifulsoup4"
            soup = BS(resp.text, "html.parser")
            for tag in soup(["script", "style", "noscript"]):
                tag.decompose()
            text = soup.get_text("\n", strip=True)
            return "\n".join(line for line in text.splitlines() if line.strip())
        except Exception as e:
            return f"Error: {e}"

    def get_page_links(self, url: str) -> str:
        try:
            sess = self._get_session()
            timeout = self._get_timeout("web_fetch", 15)
            resp = sess.get(url, timeout=timeout)
            if resp.status_code != 200:
                return f"Error: status {resp.status_code}"

            BS = bs4_beautifulsoup()
            if not BS:
                return "Install beautifulsoup4 for richer extraction: pip install beautifulsoup4"
            soup = BS(resp.text, "html.parser")
            links = []
            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                if href.startswith("#"):
                    continue
                abs_url = urllib.parse.urljoin(url, href)
                links.append(abs_url)
            uniq = sorted(set(links))
            return "\n".join(uniq[:500]) if uniq else "No links found."
        except Exception as e:
            return f"Error: {e}"

    def get_page_images(self, url: str) -> str:
        try:
            sess = self._get_session()
            timeout = self._get_timeout("web_fetch", 15)
            resp = sess.get(url, timeout=timeout)
            if resp.status_code != 200:
                return f"Error: status {resp.status_code}"

            BS = bs4_beautifulsoup()
            if not BS:
                return "Install beautifulsoup4 for richer extraction: pip install beautifulsoup4"
            soup = BS(resp.text, "html.parser")
            imgs = []
            for img in soup.find_all("img"):
                src = (img.get("src") or "").strip()
                if not src:
                    continue
                abs_url = urllib.parse.urljoin(url, src)
                imgs.append(abs_url)
            uniq = sorted(set(imgs))
            return "\n".join(uniq[:300]) if uniq else "No images found."
        except Exception as e:
            return f"Error: {e}"

    def download_file(self, url: str, dest_path: str, timeout: str = "") -> str:
        if not self.rules.get("allow_web_download", True):
            return "Error: Web download is disabled by rules."
        try:
            sess = self._get_session()
            download_timeout = (
                int(timeout) if timeout else self._get_timeout("web_download", 120)
            )
            resp = sess.get(url, stream=True, timeout=download_timeout)
            resp.raise_for_status()
            out_path = self._resolve_path_in_base(dest_path)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            size = 0
            with out_path.open("wb") as f:
                for chunk in resp.iter_content(chunk_size=1024 * 64):
                    if not chunk:
                        continue
                    f.write(chunk)
                    size += len(chunk)
            return f"Downloaded {size} bytes to {out_path}"
        except Exception as e:
            return f"Download error: {e}"
