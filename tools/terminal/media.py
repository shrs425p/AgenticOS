"""
AgenticOs — media controls mixin
Play, pause, stop, next, previous track, seek, and volume control.

Windows: SendKeys via PowerShell (WScript.Shell) + nircmd for volume.
macOS:   osascript (AppleScript) for iTunes/Music and volume.
Linux:   playerctl (MPRIS) + pactl/amixer for volume.
"""

from __future__ import annotations

import os
import shutil
import subprocess  # nosec B404



from core.tool_base import tool
class MediaMixin:
    """Media playback and audio control methods."""

    # ── internal helpers ──────────────────────────────────────────────────────

    def _nircmd_path(self) -> str:
        r"""Return path to bundled nircmd.exe (AgenticOs\core\nircmd\nircmd.exe)."""
        base = os.environ.get("AGENT_BASE_DIR", "")
        if base:
            p = os.path.join(base, "core", "nircmd", "nircmd.exe")
            if os.path.isfile(p):
                return p
        # Walk up from this file's location as fallback
        here = os.path.dirname(os.path.abspath(__file__))
        for _ in range(5):
            here = os.path.dirname(here)
            p = os.path.join(here, "core", "nircmd", "nircmd.exe")
            if os.path.isfile(p):
                return p
        return ""

    def _send_media_key(self, vk_hex: str) -> str:
        """Send a virtual-key media keystroke via PowerShell WScript.Shell."""
        ps_cmd = (
            f"$wsh = New-Object -ComObject WScript.Shell; "
            f"$wsh.SendKeys([char][int]0x{vk_hex})"
        )
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
                capture_output=True,
                text=True,
                timeout=8,
            )
            if result.returncode != 0:
                err = result.stderr.strip()
                return f"Error: {err}" if err else f"Exit code: {result.returncode}"
            return "OK"
        except Exception as e:
            return f"Error: {e}"

    def _run_nircmd(self, *args: str) -> str:
        """Run nircmd with the given args."""
        nircmd = self._nircmd_path()
        if not nircmd:
            return "Error: nircmd.exe not found in core/nircmd/."
        try:
            result = subprocess.run(
                [nircmd, *args],
                capture_output=True,
                text=True,
                timeout=8,
            )
            return result.stdout.strip() or "OK"
        except Exception as e:
            return f"Error: {e}"

    def _run_playerctl(self, *args: str) -> str:
        """Run playerctl (Linux MPRIS) with the given args."""
        if not shutil.which("playerctl"):
            return "Error: playerctl not installed. Run: sudo apt install playerctl"
        try:
            result = subprocess.run(
                ["playerctl", *args],
                capture_output=True,
                text=True,
                timeout=8,
            )
            return result.stdout.strip() or "OK"
        except Exception as e:
            return f"Error: {e}"

    def _run_osascript(self, script: str) -> str:
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=8,
            )
            return result.stdout.strip() or "OK"
        except Exception as e:
            return f"Error: {e}"

    # ── playback controls ──────────────────────────────────────────────────────

    @tool(name="media_play_pause", desc="Toggle play/pause for the active media player.", category="Terminal")
    def media_play_pause(self) -> str:
        """Toggle play/pause for the active media player."""
        if self.system == "Windows":
            return self._send_media_key("B3")  # VK_MEDIA_PLAY_PAUSE = 0xB3
        elif self.system == "Darwin":
            return self._run_osascript('tell application "Music" to playpause')
        else:
            return self._run_playerctl("play-pause")

    @tool(name="media_play", desc="Resume/start media playback.", category="Terminal")
    def media_play(self) -> str:
        """Resume / start playback."""
        if self.system == "Windows":
            return self._send_media_key("B3")  # toggle; most players resume if paused
        elif self.system == "Darwin":
            return self._run_osascript('tell application "Music" to play')
        else:
            return self._run_playerctl("play")

    @tool(name="media_pause", desc="Pause the active media player.", category="Terminal")
    def media_pause(self) -> str:
        """Pause the active media player."""
        if self.system == "Windows":
            return self._send_media_key("B3")  # toggle; most players pause if playing
        elif self.system == "Darwin":
            return self._run_osascript('tell application "Music" to pause')
        else:
            return self._run_playerctl("pause")

    @tool(name="media_stop", desc="Stop media playback.", category="Terminal")
    def media_stop(self) -> str:
        """Stop media playback."""
        if self.system == "Windows":
            return self._send_media_key("B2")  # VK_MEDIA_STOP = 0xB2
        elif self.system == "Darwin":
            return self._run_osascript('tell application "Music" to stop')
        else:
            return self._run_playerctl("stop")

    @tool(name="media_next", desc="Skip to the next track.", category="Terminal")
    def media_next(self) -> str:
        """Skip to the next track."""
        if self.system == "Windows":
            return self._send_media_key("B0")  # VK_MEDIA_NEXT_TRACK = 0xB0
        elif self.system == "Darwin":
            return self._run_osascript('tell application "Music" to next track')
        else:
            return self._run_playerctl("next")

    @tool(name="media_previous", desc="Go to the previous track.", category="Terminal")
    def media_previous(self) -> str:
        """Go back to the previous track."""
        if self.system == "Windows":
            return self._send_media_key("B1")  # VK_MEDIA_PREV_TRACK = 0xB1
        elif self.system == "Darwin":
            return self._run_osascript('tell application "Music" to previous track')
        else:
            return self._run_playerctl("previous")

    @tool(name="media_status", desc="Get currently playing track info and playback status.", category="Terminal")
    def media_status(self) -> str:
        """Get currently playing track info / playback status."""
        if self.system == "Windows":
            # Query SMTC (System Media Transport Controls) via PowerShell
            ps_cmd = r"""
try {
    Add-Type -AssemblyName System.Runtime.WindowsRuntime -ErrorAction Stop | Out-Null
    $null = [Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager,
             Windows.Media.Control, ContentType=WindowsRuntime]
    $mgr = [Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager]::RequestAsync().GetAwaiter().GetResult()
    $session = $mgr.GetCurrentSession()
    if (!$session) { Write-Output "No active media session."; exit 0 }
    $info = $session.TryGetMediaPropertiesAsync().GetAwaiter().GetResult()
    $pb   = $session.GetPlaybackInfo()
    $status = $pb.PlaybackStatus
    $title  = $info.Title
    $artist = $info.Artist
    Write-Output "Status : $status`nTitle  : $title`nArtist : $artist"
} catch {
    Write-Output "SMTC unavailable: $_"
}
"""
            out = self._run_ps(ps_cmd) if hasattr(self, "_run_ps") else ""
            if not out or "unavailable" in out.lower():
                # Lightweight fallback: check for common music processes
                players = [
                    "spotify.exe",
                    "groove.exe",
                    "musicbee.exe",
                    "vlc.exe",
                    "foobar2000.exe",
                    "wmplayer.exe",
                ]
                found = []
                for p in players:
                    try:
                        r = subprocess.run(
                            ["tasklist", "/FI", f"IMAGENAME eq {p}"],
                            capture_output=True,
                            text=True,
                            timeout=5,
                        )
                        if p.lower() in r.stdout.lower():
                            found.append(p.replace(".exe", ""))
                    except Exception:
                        pass
                if found:
                    return f"Running players: {', '.join(found)}\n(SMTC status unavailable)"
                return "No active media player detected."
            return out
        elif self.system == "Darwin":
            script = """
tell application "Music"
    if player state is playing then
        set t to name of current track
        set a to artist of current track
        return "Playing: " & t & " — " & a
    else
        return "Not playing"
    end if
end tell"""
            return self._run_osascript(script)
        else:
            status = self._run_playerctl("status")
            title = self._run_playerctl("metadata", "title")
            artist = self._run_playerctl("metadata", "artist")
            return f"Status: {status}\nTitle:  {title}\nArtist: {artist}"

    # ── seek / position ───────────────────────────────────────────────────────

    @tool(name="media_seek", desc="Seek forward/backward by N seconds. Args: seconds (+/-)", category="Terminal")
    def media_seek(self, seconds: float) -> str:
        """Seek forward (positive) or backward (negative) by N seconds.

        Args:
            seconds: Number of seconds to seek (+/-).
        """
        try:
            s = float(seconds)
        except (TypeError, ValueError):
            return "Error: seconds must be a number."

        if self.system == "Windows":
            # Windows doesn't have a universal seek key; best-effort via playerctl if available
            if shutil.which("playerctl"):
                direction = "+" if s >= 0 else ""
                return self._run_playerctl("position", f"{direction}{abs(s)}")
            return "Seek is not universally supported on Windows. Try using Spotify/VLC controls directly."
        elif self.system == "Darwin":
            script = f"""
tell application "Music"
    set player position to (player position + {s})
end tell"""
            return self._run_osascript(script)
        else:
            direction = "+" if s >= 0 else ""
            return self._run_playerctl("position", f"{direction}{abs(s)}")

    # ── volume controls ───────────────────────────────────────────────────────

    @tool(name="volume_set", desc="Set system master volume 0-100. Args: level", category="Terminal")
    def volume_set(self, level: int) -> str:
        """Set system master volume (0–100).

        Args:
            level: Volume percentage (0 = mute, 100 = max).
        """
        try:
            lvl = max(0, min(100, int(level)))
        except (TypeError, ValueError):
            return "Error: level must be 0–100."

        if self.system == "Windows":
            nircmd = self._nircmd_path()
            if nircmd:
                # nircmd setsysvolume uses 0–65535 scale
                raw = int(lvl / 100 * 65535)
                return self._run_nircmd("setsysvolume", str(raw))

            # REQUIRED FIX
            ps_alt = f"""
$lvl = {lvl}
$code = @'
using System;
using System.Runtime.InteropServices;
[Guid("5CDF2C82-841E-4546-9722-0CF74078229A"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IAudioEndpointVolume {{
    int NotImpl1(); int NotImpl2();
    int GetMasterVolumeLevel(out float pfLevelDB);
    int GetMasterVolumeLevelScalar(out float pfLevel);
    int SetMasterVolumeLevel(float fLevelDB, ref Guid pguidEventContext);
    int SetMasterVolumeLevelScalar(float fLevel, ref Guid pguidEventContext);
}}
[Guid("D666063F-1587-4E43-81F1-B948E807363F"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IMMDevice {{ int Activate(ref Guid id, int clsCtx, IntPtr pActivationParams, out IAudioEndpointVolume ppInterface); }}
[Guid("A95664D2-9614-4F35-A746-DE8DB63617E6"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IMMDeviceEnumerator {{
    int NotImpl(); int GetDefaultAudioEndpoint(int dataFlow, int role, out IMMDevice ppDevice);
}}
[ComImport, Guid("BCDE0395-E52F-467C-8E3D-C4579291692E")] class MMDeviceEnumeratorComObject {{}}
public class VolSetter {{
    public static void SetVolume(float level) {{
        var de = new MMDeviceEnumeratorComObject() as IMMDeviceEnumerator;
        IMMDevice dev; de.GetDefaultAudioEndpoint(0, 1, out dev);
        var aevGuid = typeof(IAudioEndpointVolume).GUID;
        IAudioEndpointVolume aev; dev.Activate(ref aevGuid, 23, IntPtr.Zero, out aev);
        aev.SetMasterVolumeLevelScalar(level / 100f, Guid.Empty);
    }}
}}
'@
try {{
    Add-Type -TypeDefinition $code -ErrorAction Stop | Out-Null
    [VolSetter]::SetVolume($lvl)
    "Volume set to $lvl%"
}} catch {{
    "Unable to change volume: $_"
}}
"""
            result = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_alt],
                capture_output=True,
                text=True,
                timeout=12,
            )
            return result.stdout.strip() or f"Volume set to {lvl}%"

        elif self.system == "Darwin":
            return self._run_osascript(f"set volume output volume {lvl}")
        else:
            # Linux: pactl (PulseAudio/PipeWire)
            if shutil.which("pactl"):
                result = subprocess.run(
                    ["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{lvl}%"],
                    capture_output=True,
                    text=True,
                    timeout=8,
                )
                return result.stdout.strip() or f"Volume set to {lvl}%"
            elif shutil.which("amixer"):
                result = subprocess.run(
                    ["amixer", "-q", "sset", "Master", f"{lvl}%"],
                    capture_output=True,
                    text=True,
                    timeout=8,
                )
                return result.stdout.strip() or f"Volume set to {lvl}%"
            return "Error: Install pactl (PulseAudio) or amixer (ALSA)."

    @tool(name="volume_up", desc="Raise system volume by step% (default 10). Args: step(optional)", category="Terminal")
    def volume_up(self, step: int = 10) -> str:
        """Raise system volume by step% (default +10).

        Args:
            step: Percentage points to increase (1–50).
        """
        try:
            s = max(1, min(50, int(step)))
        except (TypeError, ValueError):
            s = 10

        if self.system == "Windows":
            nircmd = self._nircmd_path()
            if nircmd:
                raw = int(s / 100 * 65535)
                return self._run_nircmd("changesysvolume", str(raw))
            # Fallback: media key presses
            out_parts = []
            for _ in range(max(1, s // 2)):
                r = self._send_media_key("AF")  # VK_VOLUME_UP = 0xAF
                out_parts.append(r)
            return f"Volume increased by ~{s}%"
        elif self.system == "Darwin":
            return self._run_osascript(
                f"set volume output volume ((output volume of (get volume settings)) + {s})"
            )
        else:
            if shutil.which("pactl"):
                subprocess.run(
                    ["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"+{s}%"],
                    capture_output=True,
                    timeout=8,
                )
                return f"Volume increased by {s}%"
            elif shutil.which("amixer"):
                subprocess.run(
                    ["amixer", "-q", "sset", "Master", f"{s}%+"],
                    capture_output=True,
                    timeout=8,
                )
                return f"Volume increased by {s}%"
            return "Error: Install pactl or amixer."

    @tool(name="volume_down", desc="Lower system volume by step% (default 10). Args: step(optional)", category="Terminal")
    def volume_down(self, step: int = 10) -> str:
        """Lower system volume by step% (default -10).

        Args:
            step: Percentage points to decrease (1–50).
        """
        try:
            s = max(1, min(50, int(step)))
        except (TypeError, ValueError):
            s = 10

        if self.system == "Windows":
            nircmd = self._nircmd_path()
            if nircmd:
                raw = int(s / 100 * 65535)
                return self._run_nircmd("changesysvolume", f"-{raw}")
            for _ in range(max(1, s // 2)):
                self._send_media_key("AE")  # VK_VOLUME_DOWN = 0xAE
            return f"Volume decreased by ~{s}%"
        elif self.system == "Darwin":
            return self._run_osascript(
                f"set volume output volume ((output volume of (get volume settings)) - {s})"
            )
        else:
            if shutil.which("pactl"):
                subprocess.run(
                    ["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"-{s}%"],
                    capture_output=True,
                    timeout=8,
                )
                return f"Volume decreased by {s}%"
            elif shutil.which("amixer"):
                subprocess.run(
                    ["amixer", "-q", "sset", "Master", f"{s}%-"],
                    capture_output=True,
                    timeout=8,
                )
                return f"Volume decreased by {s}%"
            return "Error: Install pactl or amixer."

    @tool(name="volume_mute", desc="Toggle system mute on/off.", category="Terminal")
    def volume_mute(self) -> str:
        """Toggle system mute on/off."""
        if self.system == "Windows":
            nircmd = self._nircmd_path()
            if nircmd:
                return self._run_nircmd("mutesysvolume", "2")  # 2 = toggle
            return self._send_media_key("AD")  # VK_VOLUME_MUTE = 0xAD
        elif self.system == "Darwin":
            return self._run_osascript(
                "set volume with output muted (not output muted of (get volume settings))"
            )
        else:
            if shutil.which("pactl"):
                subprocess.run(
                    ["pactl", "set-sink-mute", "@DEFAULT_SINK@", "toggle"],
                    capture_output=True,
                    timeout=8,
                )
                return "Mute toggled."
            elif shutil.which("amixer"):
                subprocess.run(
                    ["amixer", "-q", "sset", "Master", "toggle"],
                    capture_output=True,
                    timeout=8,
                )
                return "Mute toggled."
            return "Error: Install pactl or amixer."

    @tool(name="volume_get", desc="Get current system master volume level.", category="Terminal")
    def volume_get(self) -> str:
        """Get the current system master volume level."""
        if self.system == "Windows":
            ps_cmd = r"""
try {
    Add-Type -AssemblyName System.Runtime.WindowsRuntime -ErrorAction SilentlyContinue | Out-Null
} catch {}
# Use nircmd as primary; fallback to WMI / SoundMixer API
nircmd = $null
$nircmdPath = (Get-Command nircmd -ErrorAction SilentlyContinue)
if ($nircmdPath) {
    # nircmd doesn't report volume; use PowerShell audio API
}
# Reliable: Windows Audio Session API via inline C#
$code = @'
using System;
using System.Runtime.InteropServices;
[Guid("77AA99A0-1BD6-484F-8BC7-2C654C9B070C"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IAudioSessionManager2 {}
[Guid("5CDF2C82-841E-4546-9722-0CF74078229A"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IAudioEndpointVolume {
    int NotImpl1(); int NotImpl2();
    int GetMasterVolumeLevel(out float pfLevelDB);
    int GetMasterVolumeLevelScalar(out float pfLevel);
    int SetMasterVolumeLevel(float fLevelDB, ref Guid pguidEventContext);
    int SetMasterVolumeLevelScalar(float fLevel, ref Guid pguidEventContext);
    int GetMute(out bool pbMute);
}
[Guid("D666063F-1587-4E43-81F1-B948E807363F"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IMMDevice { int Activate(ref Guid id, int clsCtx, IntPtr pActivationParams, out IAudioEndpointVolume ppInterface); }
[Guid("A95664D2-9614-4F35-A746-DE8DB63617E6"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IMMDeviceEnumerator {
    int NotImpl(); int GetDefaultAudioEndpoint(int dataFlow, int role, out IMMDevice ppDevice);
}
[ComImport, Guid("BCDE0395-E52F-467C-8E3D-C4579291692E")] class MMDeviceEnumeratorComObject {}
public class Vol {
    public static float GetVolume() {
        var de = new MMDeviceEnumeratorComObject() as IMMDeviceEnumerator;
        IMMDevice dev; de.GetDefaultAudioEndpoint(0, 1, out dev);
        var aevGuid = typeof(IAudioEndpointVolume).GUID;
        IAudioEndpointVolume aev; dev.Activate(ref aevGuid, 23, IntPtr.Zero, out aev);
        float v; aev.GetMasterVolumeLevelScalar(out v);
        return (float)Math.Round(v * 100);
    }
    public static bool GetMute() {
        var de = new MMDeviceEnumeratorComObject() as IMMDeviceEnumerator;
        IMMDevice dev; de.GetDefaultAudioEndpoint(0, 1, out dev);
        var aevGuid = typeof(IAudioEndpointVolume).GUID;
        IAudioEndpointVolume aev; dev.Activate(ref aevGuid, 23, IntPtr.Zero, out aev);
        bool m; aev.GetMute(out m); return m;
    }
}
'@
try {
    Add-Type -TypeDefinition $code -ErrorAction Stop | Out-Null
    $vol  = [Vol]::GetVolume()
    $mute = [Vol]::GetMute()
    "Volume: $vol% | Muted: $mute"
} catch {
    "Unable to query volume: $_"
}
"""
            result = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
                capture_output=True,
                text=True,
                timeout=12,
            )  # nosec B603 B607

            return result.stdout.strip() or "Volume query failed."
        elif self.system == "Darwin":
            return self._run_osascript("output volume of (get volume settings)")
        else:
            if shutil.which("pactl"):
                result = subprocess.run(
                    ["pactl", "get-sink-volume", "@DEFAULT_SINK@"],
                    capture_output=True,
                    text=True,
                    timeout=8,
                )  # nosec B603 B607

                return result.stdout.strip()
            elif shutil.which("amixer"):
                result = subprocess.run(
                    ["amixer", "sget", "Master"],
                    capture_output=True,
                    text=True,
                    timeout=8,
                )  # nosec B603 B607

                return result.stdout.strip()
            return "Error: Install pactl or amixer."
