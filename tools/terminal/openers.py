"""Module for openers.py"""
from __future__ import annotations

import os
import shutil
import webbrowser
from pathlib import Path
import urllib.parse
import shlex
import subprocess  # nosec B404

import time


from core.tool_base import tool
class OpenersMixin:
    @tool(name="find_app", desc="Find an app executable path (dynamic: PATH/registry/Start Menu). Args: app_name", category="Terminal")
    def find_app(self, app_name: str) -> str:
        """Find an application executable path dynamically (Windows-focused).

        Tries:
        1) PATH (shutil.which)
        2) Windows "App Paths" registry keys
        3) Start Menu shortcuts (*.lnk) by name (returns shortcut path)
        """
        name = (app_name or "").strip().strip('"').strip("'")
        if not name:
            return "Error: app_name required."

        # Normalize exe name for Windows lookups.
        exe = name
        if (
            self.system == "Windows"
            and not exe.lower().endswith(".exe")
            and " " not in exe
            and "\\" not in exe
        ):
            exe = exe + ".exe"

        try:
            resolved = shutil.which(exe) or shutil.which(name)
            if resolved:
                return resolved
        except (OSError, FileNotFoundError, TypeError):
            pass  # Expected: shutil.which may fail or return None; handled by subsequent checks.


        if self.system == "Windows":
            # Registry App Paths
            try:
                import winreg  # type: ignore

                sub = r"Software\Microsoft\Windows\CurrentVersion\App Paths"
                candidates = [
                    (winreg.HKEY_CURRENT_USER, f"{sub}\\{exe}"),
                    (winreg.HKEY_LOCAL_MACHINE, f"{sub}\\{exe}"),
                    (winreg.HKEY_CURRENT_USER, f"{sub}\\{name}"),
                    (winreg.HKEY_LOCAL_MACHINE, f"{sub}\\{name}"),
                ]
                for root, key in candidates:
                    try:
                        with winreg.OpenKey(root, key) as h:
                            val, _ = winreg.QueryValueEx(h, "")
                            if val and os.path.exists(val):
                                return val
                    except (OSError, EnvironmentError):
                        continue
            except (OSError, EnvironmentError, ImportError):
                pass  # Expected: Registry access may fail on non-Windows or restricted environments.


            # Start Menu shortcuts by name (best-effort)
            try:
                start_dirs = [
                    os.path.expandvars(
                        r"%APPDATA%\Microsoft\Windows\Start Menu\Programs"
                    ),
                    os.path.expandvars(
                        r"%ProgramData%\Microsoft\Windows\Start Menu\Programs"
                    ),
                ]
                needle = (name or "").lower()
                for sd in start_dirs:
                    if not sd or not os.path.isdir(sd):
                        continue
                    for root, _dirs, files in os.walk(sd):
                        for fn in files:
                            if not fn.lower().endswith(".lnk"):
                                continue
                            if needle and needle not in fn.lower():
                                continue
                            p = os.path.join(root, fn)
                            if os.path.exists(p):
                                return p
            except (OSError, FileNotFoundError):
                pass  # Expected: Start Menu directories may be inaccessible.


        return "Not found."

    @tool(name="open_app", desc="Open an app (dynamic discovery + launch). Args: app_name, arguments(optional)", category="Terminal")
    def open_app(self, app_name: str, arguments: str = "") -> str:
        """Open an app using dynamic discovery, then launch."""
        found = self.find_app(app_name)
        if found.startswith("Error:"):
            return found
        if found and found != "Not found.":
            # If a shortcut path, let Windows open it.
            if self.system == "Windows" and found.lower().endswith(".lnk"):
                try:
                    os.startfile(found)  # noqa: S606
                    return f"Opened shortcut: {found}"
                except Exception as e:
                    return f"Error opening shortcut: {type(e).__name__}: {e}"
            # Use launcher with resolved path, then verify process presence if possible.
            out = self.launch_application(found, arguments or "")
            try:
                # Verify by image name where possible.
                from pathlib import Path as _Path

                img = _Path(found).name
                chk = self.process_list(img)
                if chk and "No matches" not in chk and "ERROR" not in chk.upper():
                    return f"{out}\nVALIDATION: process detected ({img})".strip()
                return f"{out}\nVALIDATION: process not detected ({img})".strip()
            except (RuntimeError, OSError):
                return out  # Expected: Verification may fail; return the launch output as fallback.

        # Fallback: try by name
        return self.launch_application(app_name, arguments or "")

    @tool(name="launch_application", desc="Launch desktop application. Args: app_name, arguments (optional)", category="Terminal")
    def launch_application(self, app_name: str, arguments: str = "") -> str:
        name = (app_name or "").strip()
        if not name:
            return "Error: app_name required."
        args = (arguments or "").strip()
        cmd = f"{name} {args}".strip()

        # Prefer explicit executable resolution on Windows.
        if self.system == "Windows":
            exe = name
            if not exe.lower().endswith(".exe") and " " not in exe and "\\" not in exe:
                exe_guess = exe + ".exe"
            else:
                exe_guess = exe

            resolved = shutil.which(exe_guess) or shutil.which(exe)
            if not resolved:
                # Optional config-driven candidates if present (set by ToolRegistry).
                # Intentionally empty by default to avoid hardcoding machine-specific paths.
                cand = getattr(self, "launch_candidates", None)
                if isinstance(cand, list) and cand:
                    for c in cand:
                        try:
                            expanded = os.path.expandvars(str(c))
                            if Path(expanded).exists():
                                resolved = expanded
                                break
                        except (OSError, ValueError):
                            continue

            def _verify_running(proc_name: str) -> bool:
                try:
                    pn = proc_name.lower().strip()
                    if not pn.endswith(".exe"):
                        pn += ".exe"
                    out = self._run(f'tasklist /FI "IMAGENAME eq {pn}"', timeout=10)
                    return pn.lower() in (out or "").lower()
                except (OSError, subprocess.CalledProcessError):
                    return False  # Expected: Tasklist may fail; assume not running.


            # If we resolved an executable, launch it directly and verify.
            if resolved:
                proc_name = Path(resolved).name
                try:
                    argv = [resolved]
                    if args:
                        argv.extend(shlex.split(args, posix=False))

                    creationflags = 0
                    try:
                        creationflags = (
                            subprocess.CREATE_NEW_PROCESS_GROUP
                            | subprocess.DETACHED_PROCESS
                        )
                    except (AttributeError, ValueError):
                        creationflags = 0  # Expected: creationflags may not be available on all OS versions.


                    subprocess.Popen(argv, creationflags=creationflags, close_fds=True)  # nosec B603


                    time.sleep(0.6)
                    if _verify_running(proc_name):
                        return f"Started: {proc_name}"
                    return f"Start attempted, but process not detected: {proc_name}"
                except Exception as e:
                    return f"Error launching {proc_name}: {type(e).__name__}: {e}"

            # Fall back: ask Windows shell to try launching by name, then verify by guessed exe name.
            fallback = f'cmd /c start "" {name} {args}'.strip()
            out = self._run(fallback, timeout=10)
            time.sleep(0.6)
            guess_name = (
                exe_guess
                if exe_guess.lower().endswith(".exe")
                else (exe_guess + ".exe")
            )
            if _verify_running(guess_name):
                return f"Started: {guess_name}"
            return out or f"Start attempted, but process not detected: {guess_name}"

        return self.start_background(cmd)

    @tool(name="open_spotify_search", desc="Open Spotify search in browser/app. Args: query", category="Terminal")
    def open_spotify_search(self, query: str) -> str:
        q = (query or "").strip()
        if not q:
            return "Error: query required."
        # This opens Spotify web search; the OS may hand it off to the Spotify app.
        base_url = self.cfg.get("endpoints", {}).get("spotify_search", "https://open.spotify.com/search/")
        url = base_url + urllib.parse.quote(q)
        return self.open_url(url)

    @tool(name="open_whatsapp_web", desc="Open WhatsApp Web.", category="Terminal")
    def open_whatsapp_web(self) -> str:
        base = self.cfg.get("endpoints", {}).get("whatsapp_web", "https://web.whatsapp.com/")
        return self.open_url(base)

    @tool(name="open_whatsapp_chat", desc="Open WhatsApp chat by phone. Args: phone, message(optional)", category="Terminal")
    def open_whatsapp_chat(self, phone: str, message: str = "") -> str:
        """Open a WhatsApp chat by phone number using wa.me (prefills message if provided).

        Phone should be in international format digits only, e.g. 15551234567.
        """
        p = "".join(ch for ch in (phone or "") if ch.isdigit())
        if not p:
            return "Error: phone required (digits only, include country code)."
        base = self.cfg.get("endpoints", {}).get("whatsapp_chat", "https://wa.me/")
        url = f"{base}{p}"
        msg = (message or "").strip()
        if msg:
            url += "?text=" + urllib.parse.quote(msg)
        return self.open_url(url)

    @tool(name="open_telegram", desc="Open Telegram web or username. Args: target(optional)", category="Terminal")
    def open_telegram(self, target: str = "") -> str:
        """Open Telegram (web) or a specific username/channel."""
        t = (target or "").strip().lstrip("@")
        base_web = self.cfg.get("endpoints", {}).get("telegram_web", "https://web.telegram.org/")
        base_tme = self.cfg.get("endpoints", {}).get("telegram_tme", "https://t.me/")
        if not t:
            return self.open_url(base_web)
        return self.open_url(base_tme + urllib.parse.quote(t))

    @tool(name="open_instagram_profile", desc="Open Instagram profile. Args: username", category="Terminal")
    def open_instagram_profile(self, username: str) -> str:
        u = (username or "").strip().lstrip("@")
        if not u:
            return "Error: username required."
        base = self.cfg.get("endpoints", {}).get("instagram", "https://www.instagram.com/")
        return self.open_url(base + urllib.parse.quote(u) + "/")

    @tool(name="open_x_profile", desc="Open X/Twitter profile. Args: username", category="Terminal")
    def open_x_profile(self, username: str) -> str:
        u = (username or "").strip().lstrip("@")
        if not u:
            return "Error: username required."
        base = self.cfg.get("endpoints", {}).get("x", "https://x.com/")
        return self.open_url(base + urllib.parse.quote(u))

    @tool(name="open_facebook_profile", desc="Open Facebook profile or URL. Args: handle_or_url", category="Terminal")
    def open_facebook_profile(self, handle_or_url: str) -> str:
        h = (handle_or_url or "").strip()
        if not h:
            return "Error: handle_or_url required."
        if h.startswith("http://") or h.startswith("https://"):
            return self.open_url(h)
        base = self.cfg.get("endpoints", {}).get("facebook", "https://www.facebook.com/")
        return self.open_url(base + urllib.parse.quote(h))

    @tool(name="open_discord", desc="Open Discord in browser.", category="Terminal")
    def open_discord(self) -> str:
        base = self.cfg.get("endpoints", {}).get("discord", "https://discord.com/app")
        return self.open_url(base)

    @tool(name="open_google_search", desc="Open Google search. Args: query", category="Terminal")
    def open_google_search(self, query: str) -> str:
        q = (query or "").strip()
        if not q:
            return "Error: query required."
        base = self.cfg.get("endpoints", {}).get("google_search", "https://www.google.com/search?q=")
        return self.open_url(base + urllib.parse.quote(q))

    @tool(name="open_google_maps", desc="Open Google Maps search. Args: query", category="Terminal")
    def open_google_maps(self, query: str) -> str:
        q = (query or "").strip()
        if not q:
            return "Error: query required."
        base = self.cfg.get("endpoints", {}).get("google_maps", "https://www.google.com/maps/search/")
        return self.open_url(base + urllib.parse.quote(q))

    @tool(name="open_youtube_search", desc="Open YouTube search. Args: query", category="Terminal")
    def open_youtube_search(self, query: str) -> str:
        q = (query or "").strip()
        if not q:
            return "Error: query required."
        base = self.cfg.get("endpoints", {}).get("youtube_search", "https://www.youtube.com/results?search_query=")
        return self.open_url(base + urllib.parse.quote(q))

    @tool(name="open_github_search", desc="Open GitHub search. Args: query", category="Terminal")
    def open_github_search(self, query: str) -> str:
        q = (query or "").strip()
        if not q:
            return "Error: query required."
        base = self.cfg.get("endpoints", {}).get("github_search", "https://github.com/search?q=")
        return self.open_url(base + urllib.parse.quote(q))

    @tool(name="open_stackoverflow_search", desc="Open StackOverflow search. Args: query", category="Terminal")
    def open_stackoverflow_search(self, query: str) -> str:
        q = (query or "").strip()
        if not q:
            return "Error: query required."
        base = self.cfg.get("endpoints", {}).get("stackoverflow_search", "https://stackoverflow.com/search?q=")
        return self.open_url(base + urllib.parse.quote(q))

    @tool(name="open_file", desc="Open file with default application. Args: path", category="Terminal")
    def open_file(self, path: str) -> str:
        raw = (path or "").strip()
        if not raw:
            return "Error: path required."

        # Resolve relative paths more intuitively:
        # 1) relative to current working directory
        # 2) relative to AGENT_BASE_DIR (repo root)
        # 3) relative to repo workspace
        p = Path(raw).expanduser()
        candidates: list[Path] = []
        if p.is_absolute():
            candidates = [p]
        else:
            candidates.append(Path.cwd() / p)
            base = os.environ.get("AGENT_BASE_DIR", "").strip()
            if base:
                base_p = Path(base)
                candidates.append(base_p / p)
                candidates.append(base_p / "workspace" / p)

        picked: Path | None = None
        for c in candidates:
            try:
                c2 = c.resolve()
            except (OSError, ValueError):
                c2 = c  # Expected: Resolve may fail on invalid paths; fallback to raw path.

            if c2.exists():
                picked = c2
                break

        if not picked:
            return f"Error: file not found: {path}"

        if self.system == "Windows":
            os.startfile(str(picked))  # noqa: S606
            return "Opened."
        return self._run(f"xdg-open {self._quote_arg(str(picked))}", timeout=15)

    @tool(name="open_url", desc="Open URL in default browser. Args: url", category="Terminal")
    def open_url(self, url: str) -> str:
        try:
            webbrowser.open(url)
            return "Opened."
        except Exception as e:
            return f"Error: {e}"

    def compose_email(
        self,
        to: str = "",
        subject: str = "",
        body: str = "",
        cc: str = "",
        bcc: str = "",
    ) -> str:
        """Compose an email and open it in the default mail client using a mailto: URI.

        All fields are optional but at least 'to' is recommended.

        Args:
            to:      Recipient address(es), comma-separated (e.g. alice@example.com)
            subject: Email subject line
            body:    Email body text (plain text)
            cc:      CC address(es), comma-separated
            bcc:     BCC address(es), comma-separated
        """
        to_part = urllib.parse.quote((to or "").strip(), safe="@,")
        params: list[str] = []
        if subject:
            params.append("subject=" + urllib.parse.quote(subject.strip()))
        if body:
            params.append("body=" + urllib.parse.quote(body.strip()))
        if cc:
            params.append("cc=" + urllib.parse.quote((cc or "").strip(), safe="@,"))
        if bcc:
            params.append("bcc=" + urllib.parse.quote((bcc or "").strip(), safe="@,"))

        mailto_url = "mailto:" + to_part
        if params:
            mailto_url += "?" + "&".join(params)

        try:
            webbrowser.open(mailto_url)
            return f"Opened mail composer: {mailto_url}"
        except Exception as e:
            return f"Error opening mail client: {type(e).__name__}: {e}"

    @tool(name="open_url_verified", desc="Open URL and verify a browser process exists (best-effort). Args: url", category="Terminal")
    def open_url_verified(self, url: str) -> str:
        """Open a URL and best-effort verify that a browser process exists."""
        out = self.open_url(url)
        if self.system != "Windows":
            return out
        try:
            # Weak signal verification: check common browsers. This avoids hardcoding exact exe paths.
            checks = []
            for img in ("chrome.exe", "msedge.exe", "brave.exe", "firefox.exe"):
                r = self.process_list(img)
                if r and "No matches" not in r:
                    checks.append(img)
            if checks:
                return (
                    out
                    + f"\nVALIDATION: browser process detected ({', '.join(checks[:3])})"
                )
            return out + "\nVALIDATION: browser process not detected"
        except (RuntimeError, OSError):
            return out  # Expected: Process verification may fail; return launch result.

