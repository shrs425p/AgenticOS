"""
AgenticOs — notification tools
Cross-platform desktop notifications, popups, and TTS.
Supports Windows, macOS, and Linux.
"""

import os
import platform
import subprocess
import ctypes


from core.tool_base import tool
class NotificationCenter:
    def __init__(self, rules: dict = None):
        self.rules = rules or {}
        self.system = platform.system()  # 'Windows', 'Darwin', 'Linux'

    @tool(name="set_wallpaper", desc="Set desktop wallpaper. Args: image_path", category="General")
    def set_wallpaper(self, image_path: str) -> str:
        """Set the desktop wallpaper using a local image file."""
        try:
            # Note: Path resolution should be handled by the caller or passed as absolute
            if not os.path.exists(image_path):
                return f"Error: Image not found at {image_path}"

            if self.system == "Windows":
                ctypes.windll.user32.SystemParametersInfoW(20, 0, str(image_path), 3)
                return f"Wallpaper successfully set to {image_path}"
            elif self.system == "Darwin":
                script = f'tell application "System Events" to set picture of every desktop to "{image_path}"'
                subprocess.run(["osascript", "-e", script], check=False)
                return f"Wallpaper set via AppleScript: {image_path}"
            else:
                try:
                    subprocess.run(
                        [
                            "gsettings",
                            "set",
                            "org.gnome.desktop.background",
                            "picture-uri",
                            f"file://{image_path}",
                        ]
                    )
                    return f"Wallpaper set (Gnome): {image_path}"
                except Exception:
                    return f"Set wallpaper not fully implemented for this Linux environment. Path: {image_path}"
        except Exception as e:
            return f"Error setting wallpaper: {e}"

    # ── Internal helpers ──────────────────────────────────────────────────────
    def _run_ps(self, cmd: str) -> str:
        """Run a PowerShell command (Windows only)."""
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0 and result.stderr.strip():
                return f"PowerShell error: {result.stderr.strip()}"
            return result.stdout.strip() or "Success"
        except FileNotFoundError:
            return "Error: PowerShell not found."
        except Exception as e:
            return f"Error: {e}"

    def _run(self, args: list, timeout: int = 10) -> str:
        """Run a subprocess command."""
        try:
            result = subprocess.run(
                args, capture_output=True, text=True, timeout=timeout
            )
            return result.stdout.strip() or "Success"
        except FileNotFoundError:
            return f"Error: Command not found: {args[0]}"
        except Exception as e:
            return f"Error: {e}"

    # ── Notifications ─────────────────────────────────────────────────────────
    @tool(name="send_notification", desc="Send desktop alert. Args: title, message", category="General")
    def send_notification(self, title: str, message: str) -> str:
        """Send a desktop notification (cross-platform)."""
        title = title.replace('"', '\\"').replace("'", "\\'")
        message = message.replace('"', '\\"').replace("'", "\\'")

        if self.system == "Windows":
            ps_cmd = f"""
[void][System.Reflection.Assembly]::LoadWithPartialName("System.Windows.Forms");
$n = New-Object System.Windows.Forms.NotifyIcon;
$n.Icon = [System.Drawing.SystemIcons]::Information;
$n.BalloonTipTitle = "{title}";
$n.BalloonTipText  = "{message}";
$n.Visible = $true;
$n.ShowBalloonTip(5000);
Start-Sleep -Seconds 1;
$n.Dispose();
"""
            return self._run_ps(ps_cmd)

        elif self.system == "Darwin":
            script = f'display notification "{message}" with title "{title}"'
            return self._run(["osascript", "-e", script])

        else:
            # Linux — try notify-send, then zenity, then fallback
            import shutil

            if shutil.which("notify-send"):
                return self._run(["notify-send", title, message])
            elif shutil.which("zenity"):
                return self._run(
                    ["zenity", "--notification", f"--text={title}: {message}"]
                )
            else:
                print(f"[Notification] {title}: {message}")
                return "Notification printed to console (notify-send not available)."

    # ── Popups ────────────────────────────────────────────────────────────────
    @tool(name="show_popup", desc="Show popup message box. Args: title, message", category="General")
    def show_popup(self, title: str, message: str) -> str:
        """Show a modal popup message box (cross-platform)."""
        title = title.replace('"', '\\"').replace("'", "\\'")
        message = message.replace('"', '\\"').replace("'", "\\'")

        if self.system == "Windows":
            ps_cmd = f"""
Add-Type -AssemblyName System.Windows.Forms;
[System.Windows.Forms.MessageBox]::Show("{message}", "{title}");
"""
            return self._run_ps(ps_cmd)

        elif self.system == "Darwin":
            script = f'display dialog "{message}" with title "{title}" buttons {{"OK"}} default button "OK"'
            return self._run(["osascript", "-e", script])

        else:
            import shutil

            if shutil.which("zenity"):
                return self._run(
                    ["zenity", "--info", f"--title={title}", f"--text={message}"]
                )
            elif shutil.which("xmessage"):
                return self._run(["xmessage", "-center", f"{title}\n{message}"])
            else:
                print(f"[Popup] {title}: {message}")
                return "Popup printed to console (zenity not available)."

    # ── Text-to-speech ────────────────────────────────────────────────────────
    @tool(name="speak", desc="Text-to-speech. Args: text", category="General")
    def speak(self, text: str) -> str:
        """Speak text using the system's TTS engine (cross-platform)."""
        safe = text.replace('"', '\\"').replace("'", "\\'")

        if self.system == "Windows":
            ps_cmd = f"""
Add-Type -AssemblyName System.Speech;
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer;
$synth.Speak("{safe}");
"""
            return self._run_ps(ps_cmd)

        elif self.system == "Darwin":
            return self._run(["say", text])

        else:
            import shutil

            if shutil.which("espeak"):
                return self._run(["espeak", text])
            elif shutil.which("espeak-ng"):
                return self._run(["espeak-ng", text])
            elif shutil.which("festival"):
                proc = subprocess.Popen(
                    ["festival", "--tts"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                proc.communicate(input=text.encode())
                return "Success"
            else:
                print(f"[TTS] {text}")
                return "TTS printed to console (espeak not available)."

    # ── Combined alert ────────────────────────────────────────────────────────
    @tool(name="alert", desc="Notify and speak. Args: message", category="General")
    def alert(self, message: str) -> str:
        """Send a desktop notification AND speak the message."""
        n_result = self.send_notification("AgenticOs Alert", message)
        s_result = self.speak(message)
        return (
            f"Alert sent: {message}\n  Notification: {n_result}\n  Speech: {s_result}"
        )
