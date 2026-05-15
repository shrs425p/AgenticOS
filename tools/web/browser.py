"""
AgenticOs — browser automation tools
Playwright-based browser automation: navigate, read DOM, click, fill forms,
execute JS, take screenshots, manage cookies, and more.

Installation (one-time):
    pip install playwright
    playwright install chromium
"""

from __future__ import annotations

import asyncio
import json
import os
import threading
from pathlib import Path
from typing import Any, Optional
import functools
import urllib.parse


def _async_playwright():
    """Lazy import of Playwright's async API."""
    try:
        from playwright.async_api import async_playwright

        return async_playwright
    except ImportError:
        return None


class BrowserManager:
    """Manages a dedicated background thread with its own asyncio loop for Playwright."""

    def __init__(self):
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.thread: Optional[threading.Thread] = None
        self.pw: Any = None
        self.browser: Any = None
        self.context: Any = None
        self.page: Any = None
        self.browser_type: str = "chromium"
        self._ready = threading.Event()
        self._started = False

    def start(self):
        if self._started:
            return
        self.thread = threading.Thread(
            target=self._run_loop, daemon=True, name=f"PlaywrightThread-{id(self)}"
        )
        self.thread.start()
        self._ready.wait()
        self._started = True

    def _run_loop(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self._ready.set()
        self.loop.run_forever()

    def run_coro(self, coro):
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        return future.result()

    async def cleanup(self):
        if self.page:
            try:
                await self.page.close()
            except Exception:
                pass
            self.page = None
        if self.context:
            try:
                await self.context.close()
            except Exception:
                pass
            self.context = None
        if self.browser:
            try:
                await self.browser.close()
            except Exception:
                pass
            self.browser = None
        if self.pw:
            try:
                await self.pw.stop()
            except Exception:
                pass
            self.pw = None


def _ensure_browser(fn):
    """Decorator to ensure Playwright commands run in the instance's background loop."""

    @functools.wraps(fn)
    def wrapper(self, *args, **kwargs):
        # Retrieve mgr from the host instance (e.g., WebTools)
        mgr = getattr(self, "browser_mgr", None)
        if mgr is None:
            return "Error: BrowserManager not initialized on tool host."
        mgr.start()
        return mgr.run_coro(fn(self, mgr, *args, **kwargs))

    return wrapper


_INSTALL_HINT = (
    "Playwright not installed.\n"
    "Run these commands to install:\n"
    "  pip install playwright\n"
    "  playwright install chromium"
)


class BrowserMixin:
    """Full browser automation via Playwright (async API, thread-safe wrapper)."""

    def _require_page(self, mgr: BrowserManager) -> str | None:
        if mgr.page is None:
            return "Error: No browser session active. Call browser_launch() first."
        return None

    def _screenshot_path(self, path: str = "") -> str:
        if not path:
            from datetime import datetime

            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            fmt = self.cfg.get("prompts", {}).get("file_templates", {}).get("browser_screenshot", "browser_screenshot_{ts}.png")
            path = fmt.format(ts=ts)
        p = Path(path)
        if not p.is_absolute():
            base = getattr(self, "base_dir", Path("workspace"))
            shots_dir = Path(base) / "screenshots"
            shots_dir.mkdir(parents=True, exist_ok=True)
            p = shots_dir / p
        p.parent.mkdir(parents=True, exist_ok=True)
        return str(p)

    @_ensure_browser
    async def browser_launch(
        self,
        mgr: BrowserManager,
        browser: str = "chromium",
        headless: str = "true",
        user_data_dir: str = "",
    ) -> str:
        apw = _async_playwright()
        if apw is None:
            return _INSTALL_HINT

        await mgr.cleanup()

        headless_bool = str(headless).lower() not in ("false", "0", "no")
        b_type = (browser or "chromium").lower().strip()
        if b_type not in ("chromium", "firefox", "webkit"):
            b_type = "chromium"

        chromium_args = ["--disable-blink-features=AutomationControlled"]

        try:
            mgr.pw = await apw().start()
            launcher = getattr(mgr.pw, b_type)
            udd = (user_data_dir or "").strip()

            if udd and os.path.isdir(udd):
                browser_cfg = self.cfg.get("browser", {})
                mgr.context = await launcher.launch_persistent_context(
                    udd,
                    headless=headless_bool,
                    args=chromium_args if b_type == "chromium" else [],
                    viewport=browser_cfg.get("viewport", {"width": 1280, "height": 900}),
                )
                mgr.browser = None
                pages = mgr.context.pages
                mgr.page = pages[0] if pages else await mgr.context.new_page()
            else:
                browser_cfg = self.cfg.get("browser", {})
                mgr.browser = await launcher.launch(
                    headless=headless_bool,
                    args=chromium_args if b_type == "chromium" else [],
                )
                mgr.context = await mgr.browser.new_context(
                    user_agent=browser_cfg.get("user_agent", (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0.0.0 Safari/537.36"
                    )),
                    viewport=browser_cfg.get("viewport", {"width": 1280, "height": 900}),
                )
                mgr.page = await mgr.context.new_page()

            mgr.browser_type = b_type
            mode = "headless" if headless_bool else "headed"
            return f"Browser launched: {b_type} [{mode}]"
        except Exception as e:
            await mgr.cleanup()
            return f"Error launching browser: {type(e).__name__}: {e}"

    @_ensure_browser
    async def browser_close(self, mgr: BrowserManager) -> str:
        await mgr.cleanup()
        return "Browser session closed."

    @_ensure_browser
    async def browser_status(self, mgr: BrowserManager) -> str:
        err = self._require_page(mgr)
        if err:
            return err
        try:
            url = mgr.page.url or "(blank)"
            title = await mgr.page.title() or "(no title)"
            n_tabs = len(mgr.context.pages) if mgr.context else 0
            return f"Browser: {mgr.browser_type}\nURL: {url}\nTitle: {title}\nTabs: {n_tabs}"
        except Exception as e:
            return f"Error: {type(e).__name__}: {e}"

    @_ensure_browser
    async def browser_navigate(
        self, mgr: BrowserManager, url: str, wait_until: str = "domcontentloaded"
    ) -> str:
        err = self._require_page(mgr)
        if err:
            return err
        wu = (wait_until or "domcontentloaded").lower()
        if wu not in {"load", "domcontentloaded", "networkidle", "commit"}:
            wu = "domcontentloaded"
        try:
            t = self._get_timeout("browser_nav", 30000)
            resp = await mgr.page.goto(url, wait_until=wu, timeout=t)
            status = resp.status if resp else "?"
            return f"Navigated to: {mgr.page.url}\nTitle: {await mgr.page.title()}\nHTTP status: {status}"
        except Exception as e:
            return f"Navigation error: {type(e).__name__}: {e}"

    @_ensure_browser
    async def browser_go_back(self, mgr: BrowserManager) -> str:
        err = self._require_page(mgr)
        if err:
            return err
        try:
            t = self._get_timeout("browser_action", 15000)
            await mgr.page.go_back(wait_until="domcontentloaded", timeout=t)
            return f"Back → {mgr.page.url}"
        except Exception as e:
            return f"Error: {type(e).__name__}: {e}"

    @_ensure_browser
    async def browser_go_forward(self, mgr: BrowserManager) -> str:
        err = self._require_page(mgr)
        if err:
            return err
        try:
            t = self._get_timeout("browser_action", 15000)
            await mgr.page.go_forward(wait_until="domcontentloaded", timeout=t)
            return f"Forward → {mgr.page.url}"
        except Exception as e:
            return f"Error: {type(e).__name__}: {e}"

    @_ensure_browser
    async def browser_reload(self, mgr: BrowserManager) -> str:
        err = self._require_page(mgr)
        if err:
            return err
        try:
            t = self._get_timeout("browser_action", 15000)
            await mgr.page.reload(wait_until="domcontentloaded", timeout=t)
            return f"Reloaded: {mgr.page.url}"
        except Exception as e:
            return f"Error: {type(e).__name__}: {e}"

    @_ensure_browser
    async def browser_new_tab(self, mgr: BrowserManager, url: str = "") -> str:
        err = self._require_page(mgr)
        if err:
            return err
        try:
            page = await mgr.context.new_page()
            mgr.page = page
            if url:
                t = self._get_timeout("browser_nav", 30000)
                await page.goto(url, wait_until="domcontentloaded", timeout=t)
                return f"New tab opened: {page.url}"
            return "New tab opened (blank)."
        except Exception as e:
            return f"Error: {type(e).__name__}: {e}"

    @_ensure_browser
    async def browser_get_url(self, mgr: BrowserManager) -> str:
        err = self._require_page(mgr)
        if err:
            return err
        return mgr.page.url

    @_ensure_browser
    async def browser_get_title(self, mgr: BrowserManager) -> str:
        err = self._require_page(mgr)
        if err:
            return err
        return await mgr.page.title()

    @_ensure_browser
    async def browser_get_text(self, mgr: BrowserManager) -> str:
        err = self._require_page(mgr)
        if err:
            return err
        try:
            text = await mgr.page.evaluate("() => document.body.innerText")
            if not text:
                return "(page appears empty or has no visible text)"
            result = "\n".join([ln for ln in text.splitlines() if ln.strip()])
            limit = int(self.cfg.get("browser", {}).get("text_truncation_limit", 20000))
            return result[:limit] + ("\n... [truncated]" if len(result) > limit else "")
        except Exception as e:
            return f"Error: {type(e).__name__}: {e}"

    @_ensure_browser
    async def browser_get_html(self, mgr: BrowserManager) -> str:
        err = self._require_page(mgr)
        if err:
            return err
        try:
            html = await mgr.page.content()
            limit = int(self.cfg.get("browser", {}).get("html_truncation_limit", 50000))
            return html[:limit] + ("\n... [truncated]" if len(html) > limit else "")
        except Exception as e:
            return f"Error: {type(e).__name__}: {e}"

    @_ensure_browser
    async def browser_get_element_text(self, mgr: BrowserManager, selector: str) -> str:
        err = self._require_page(mgr)
        if err:
            return err
        try:
            t = self._get_timeout("browser_action", 5000)
            await mgr.page.wait_for_selector(selector, timeout=t)
            text = await mgr.page.inner_text(selector)
            return text or "(element empty)"
        except Exception as e:
            return f"Error: {type(e).__name__}: {e}"

    @_ensure_browser
    async def browser_get_elements(self, mgr: BrowserManager, selector: str) -> str:
        err = self._require_page(mgr)
        if err:
            return err
        try:
            els = await mgr.page.query_selector_all(selector)
            if not els:
                return f"No elements found: {selector}"
            lines = [f"Found {len(els)} element(s):"]
            for i, el in enumerate(els[:50]):
                tag = await el.evaluate("e => e.tagName.toLowerCase()")
                txt = (await el.inner_text() or "").strip()[:80]
                lines.append(f"  [{i}] <{tag}> {txt!r}")
            return "\n".join(lines)
        except Exception as e:
            return f"Error: {type(e).__name__}: {e}"

    @_ensure_browser
    async def browser_get_links(self, mgr: BrowserManager) -> str:
        err = self._require_page(mgr)
        if err:
            return err
        try:
            links = await mgr.page.evaluate(
                r"""() => Array.from(document.querySelectorAll('a[href]')).map(a => a.innerText.trim().substring(0,80) + ' → ' + a.href)"""
            )
            return "\n".join(links[:300])
        except Exception as e:
            return f"Error: {type(e).__name__}: {e}"

    @_ensure_browser
    async def browser_get_inputs(self, mgr: BrowserManager) -> str:
        err = self._require_page(mgr)
        if err:
            return err
        try:
            fields = await mgr.page.evaluate(
                r"""() => Array.from(document.querySelectorAll('input,textarea,select,button[type=submit]')).map(el => ({tag: el.tagName.toLowerCase(), type: el.type, name: el.name||el.id, value: el.value.substring(0,80)}))"""
            )
            return "\n".join(
                [
                    f"<{f['tag']} type={f['type']}> name={f['name']} val={f['value']}"
                    for f in fields[:100]
                ]
            )
        except Exception as e:
            return f"Error: {type(e).__name__}: {e}"

    @_ensure_browser
    async def browser_click(self, mgr: BrowserManager, selector: str) -> str:
        err = self._require_page(mgr)
        if err:
            return err
        try:
            t = self._get_timeout("browser_action", 10000)
            await mgr.page.click(selector, timeout=t)
            return f"Clicked: {selector}"
        except Exception as e:
            return f"Error: {type(e).__name__}: {e}"

    @_ensure_browser
    async def browser_fill(self, mgr: BrowserManager, selector: str, value: str) -> str:
        err = self._require_page(mgr)
        if err:
            return err
        try:
            t = self._get_timeout("browser_action", 10000)
            await mgr.page.fill(selector, value, timeout=t)
            return f"Filled {selector}"
        except Exception as e:
            return f"Error: {type(e).__name__}: {e}"

    @_ensure_browser
    async def browser_type(
        self, mgr: BrowserManager, selector: str, text: str, delay_ms: str = "50"
    ) -> str:
        err = self._require_page(mgr)
        if err:
            return err
        try:
            d = int(delay_ms) if str(delay_ms).isdigit() else 50
            t = self._get_timeout("browser_action", 10000)
            await mgr.page.type(selector, text, delay=d, timeout=t)
            return f"Typed into {selector}"
        except Exception as e:
            return f"Error: {type(e).__name__}: {e}"

    @_ensure_browser
    async def browser_press_key(self, mgr: BrowserManager, key: str) -> str:
        err = self._require_page(mgr)
        if err:
            return err
        try:
            await mgr.page.keyboard.press(key)
            return f"Pressed {key}"
        except Exception as e:
            return f"Error: {type(e).__name__}: {e}"

    @_ensure_browser
    async def browser_scroll(
        self, mgr: BrowserManager, direction: str = "down", amount: str = "500"
    ) -> str:
        err = self._require_page(mgr)
        if err:
            return err
        try:
            px = int(amount) if str(amount).lstrip("-").isdigit() else 500
            if direction == "top":
                await mgr.page.evaluate("window.scrollTo(0,0)")
            elif direction == "bottom":
                await mgr.page.evaluate(
                    "window.scrollTo(0, document.body.scrollHeight)"
                )
            elif direction == "up":
                await mgr.page.evaluate(f"window.scrollBy(0, -{px})")
            else:
                await mgr.page.evaluate(f"window.scrollBy(0, {px})")
            return f"Scrolled {direction}"
        except Exception as e:
            return f"Error: {type(e).__name__}: {e}"

    @_ensure_browser
    async def browser_wait_for(
        self, mgr: BrowserManager, selector: str, timeout_ms: str = "10000"
    ) -> str:
        err = self._require_page(mgr)
        if err:
            return err
        try:
            t = int(timeout_ms) if str(timeout_ms).isdigit() else self._get_timeout("browser_action", 10000)
            await mgr.page.wait_for_selector(selector, timeout=t)
            return f"Appeared: {selector}"
        except Exception:
            return f"Timeout: {selector}"

    @_ensure_browser
    async def browser_execute_js(self, mgr: BrowserManager, code: str) -> str:
        err = self._require_page(mgr)
        if err:
            return err
        try:
            res = await mgr.page.evaluate(f"() => {{ {code} }}")
            return json.dumps(res, indent=2) if res is not None else "(null)"
        except Exception as e:
            return f"JS Error: {e}"

    @_ensure_browser
    async def browser_screenshot(
        self, mgr: BrowserManager, path: str = "", full_page: str = "false"
    ) -> str:
        err = self._require_page(mgr)
        if err:
            return err
        try:
            out = self._screenshot_path(path)
            fp = str(full_page).lower() not in ("false", "0", "no")
            await mgr.page.screenshot(path=out, full_page=fp)
            return f"Screenshot: {out}"
        except Exception as e:
            return f"Error: {e}"

    @_ensure_browser
    async def browser_select(
        self, mgr: BrowserManager, selector: str, value: str
    ) -> str:
        err = self._require_page(mgr)
        if err:
            return err
        try:
            t = self._get_timeout("browser_action", 10000)
            selected = await mgr.page.select_option(
                selector, value=value, timeout=t
            )
            return f"Selected {selected} in {selector}"
        except Exception as e:
            return f"Error: {e}"

    @_ensure_browser
    async def browser_get_cookies(self, mgr: BrowserManager) -> str:
        err = self._require_page(mgr)
        if err:
            return err
        try:
            cookies = await mgr.context.cookies()
            return "\n".join([f"{c['name']}={c['value'][:60]}" for c in cookies[:100]])
        except Exception as e:
            return f"Error: {e}"

    @_ensure_browser
    async def browser_set_cookie(
        self,
        mgr: BrowserManager,
        name: str,
        value: str,
        domain: str = "",
        path: str = "/",
    ) -> str:
        err = self._require_page(mgr)
        if err:
            return err
        try:
            d = domain or urllib.parse.urlparse(mgr.page.url).netloc
            await mgr.context.add_cookies(
                [{"name": name, "value": value, "domain": d, "path": path}]
            )
            return f"Cookie set: {name}"
        except Exception as e:
            return f"Error: {e}"

    @_ensure_browser
    async def browser_clear_cookies(self, mgr: BrowserManager) -> str:
        err = self._require_page(mgr)
        if err:
            return err
        try:
            await mgr.context.clear_cookies()
            return "Cookies cleared."
        except Exception as e:
            return f"Error: {e}"

    @_ensure_browser
    async def browser_check(
        self, mgr: BrowserManager, selector: str, checked: str = "true"
    ) -> str:
        err = self._require_page(mgr)
        if err:
            return err
        try:
            t = self._get_timeout("browser_action", 10000)
            if str(checked).lower() not in ("false", "0", "no"):
                await mgr.page.check(selector, timeout=t)
                return f"Checked: {selector}"
            else:
                await mgr.page.uncheck(selector, timeout=t)
                return f"Unchecked: {selector}"
        except Exception as e:
            return f"Error: {e}"
