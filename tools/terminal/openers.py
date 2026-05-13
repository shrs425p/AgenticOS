from __future__ import annotations

import os
import shutil
import webbrowser
from pathlib import Path
import urllib.parse
import shlex
import subprocess
import time


class OpenersMixin:
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
        except Exception:
            pass

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
                    except Exception:
                        continue
            except Exception:
                pass

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
            except Exception:
                pass

        return "Not found."

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
            except Exception:
                return out
        # Fallback: try by name
        return self.launch_application(app_name, arguments or "")

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
                        except Exception:
                            continue

            def _verify_running(proc_name: str) -> bool:
                try:
                    pn = proc_name.lower().strip()
                    if not pn.endswith(".exe"):
                        pn += ".exe"
                    out = self._run(f'tasklist /FI "IMAGENAME eq {pn}"', timeout=10)
                    return pn.lower() in (out or "").lower()
                except Exception:
                    return False

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
                    except Exception:
                        creationflags = 0

                    subprocess.Popen(argv, creationflags=creationflags, close_fds=True)
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

    def open_spotify_search(self, query: str) -> str:
        q = (query or "").strip()
        if not q:
            return "Error: query required."
        # This opens Spotify web search; the OS may hand it off to the Spotify app.
        url = "https://open.spotify.com/search/" + urllib.parse.quote(q)
        return self.open_url(url)

    def open_whatsapp_web(self) -> str:
        return self.open_url("https://web.whatsapp.com/")

    def open_whatsapp_chat(self, phone: str, message: str = "") -> str:
        """Open a WhatsApp chat by phone number using wa.me (prefills message if provided).

        Phone should be in international format digits only, e.g. 15551234567.
        """
        p = "".join(ch for ch in (phone or "") if ch.isdigit())
        if not p:
            return "Error: phone required (digits only, include country code)."
        url = f"https://wa.me/{p}"
        msg = (message or "").strip()
        if msg:
            url += "?text=" + urllib.parse.quote(msg)
        return self.open_url(url)

    def open_telegram(self, target: str = "") -> str:
        """Open Telegram (web) or a specific username/channel."""
        t = (target or "").strip().lstrip("@")
        if not t:
            return self.open_url("https://web.telegram.org/")
        return self.open_url("https://t.me/" + urllib.parse.quote(t))

    def open_instagram_profile(self, username: str) -> str:
        u = (username or "").strip().lstrip("@")
        if not u:
            return "Error: username required."
        return self.open_url("https://www.instagram.com/" + urllib.parse.quote(u) + "/")

    def open_x_profile(self, username: str) -> str:
        u = (username or "").strip().lstrip("@")
        if not u:
            return "Error: username required."
        return self.open_url("https://x.com/" + urllib.parse.quote(u))

    def open_facebook_profile(self, handle_or_url: str) -> str:
        h = (handle_or_url or "").strip()
        if not h:
            return "Error: handle_or_url required."
        if h.startswith("http://") or h.startswith("https://"):
            return self.open_url(h)
        return self.open_url("https://www.facebook.com/" + urllib.parse.quote(h))

    def open_discord(self) -> str:
        return self.open_url("https://discord.com/app")

    def open_google_search(self, query: str) -> str:
        q = (query or "").strip()
        if not q:
            return "Error: query required."
        return self.open_url("https://www.google.com/search?q=" + urllib.parse.quote(q))

    def open_google_maps(self, query: str) -> str:
        q = (query or "").strip()
        if not q:
            return "Error: query required."
        return self.open_url(
            "https://www.google.com/maps/search/" + urllib.parse.quote(q)
        )

    def open_youtube_search(self, query: str) -> str:
        q = (query or "").strip()
        if not q:
            return "Error: query required."
        return self.open_url(
            "https://www.youtube.com/results?search_query=" + urllib.parse.quote(q)
        )

    def open_github_search(self, query: str) -> str:
        q = (query or "").strip()
        if not q:
            return "Error: query required."
        return self.open_url("https://github.com/search?q=" + urllib.parse.quote(q))

    def open_stackoverflow_search(self, query: str) -> str:
        q = (query or "").strip()
        if not q:
            return "Error: query required."
        return self.open_url(
            "https://stackoverflow.com/search?q=" + urllib.parse.quote(q)
        )

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
            except Exception:
                c2 = c
            if c2.exists():
                picked = c2
                break

        if not picked:
            return f"Error: file not found: {path}"

        if self.system == "Windows":
            os.startfile(str(picked))  # noqa: S606
            return "Opened."
        return self._run(f"xdg-open {self._quote_arg(str(picked))}", timeout=15)

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
        except Exception:
            return out
