"""Tool registration and dispatch for the AgenticOs runtime."""

import inspect
import urllib.parse
import time
import ast
import math
import operator
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable

from tools import desktop_notifications as notifications
from tools import filesystem_tools as filesystem
from tools import screen_tools as screen
from tools import terminal_tools as terminal
from tools import web_tools as web
from tools.web_pick_best_link import web_pick_best_link

from core.runtime_config import DEFAULT_WORKSPACE
from core.url_presets import load_url_presets
from core.validators import validate_tool
from .guardrails import PathGuard

import importlib.util
import os
import sys


def tool(
    name: str = None,
    desc: str = None,
    category: str = "general",
    version: str = "1.0.0",
    author: str = "AgenticOs",
):
    """Decorator to mark a function as a tool for AgenticOs."""

    def decorator(func):
        func._is_tool = True
        func._tool_name = name or func.__name__
        doc = func.__doc__ or "No description provided."
        func._tool_desc = desc or doc.strip().split("\n")[0]
        func._tool_category = category
        func._tool_version = version
        func._tool_author = author
        return func

    return decorator


class ToolRegistry:
    def __init__(
        self,
        cfg: dict,
        memory_backend: Optional[Any] = None,
        confirm_handler: Optional[Callable] = None,
    ):
        self.cfg = cfg
        # Merge security + rules; security.hard_guardrails indicates some restrictions are never bypassed.
        self.rules = {**cfg.get("security", {}), **cfg["rules"]}
        self.tools_cfg = cfg.get("tools", {})
        self._memory = memory_backend

        workspace = self.cfg.get("agent", {}).get("workspace", DEFAULT_WORKSPACE)
        self.fm = filesystem.FileManager(rules=self.rules, base_dir=workspace)
        self.term = terminal.TerminalExecutor(
            rules=self.rules,
            custom_keys=cfg.get("custom_keys", {}),
        )
        self.web = web.WebTools(rules=self.rules, base_dir=workspace, cfg=self.cfg)
        self.ui = notifications.NotificationCenter(rules=self.rules)
        self.screen = screen.ScreenManager(rules=self.rules, base_dir=workspace)
        self._notepad: List[str] = []
        self._canvas: str = ""
        self.registry: Dict[str, Dict[str, Any]] = {}
        self._register_all()
        self._load_plugins()  # <--- Load dynamic plugins
        self._workspace_root = Path(workspace).resolve()
        self.guard = PathGuard(cfg, on_confirm=confirm_handler)
        self.shadow_mode = False

    def _register_all(self):
        if self.tools_cfg.get("files", True):
            file_tools = [
                (
                    "read_file",
                    self.fm.read_file,
                    "Read file. Args: path, start_line (optional), num_lines (optional)",
                ),
                (
                    "write_file",
                    self.fm.write_file,
                    "Write/overwrite a file. Args: path, content",
                ),
                (
                    "append_file",
                    self.fm.append_file,
                    "Append to a file. Args: path, content",
                ),
                ("delete_file", self.fm.delete_file, "Delete a file. Args: path"),
                (
                    "list_dir",
                    self.fm.list_dir,
                    "List directory contents. Args: path (optional)",
                ),
                ("create_dir", self.fm.create_dir, "Create directory. Args: path"),
                (
                    "delete_dir",
                    self.fm.delete_dir,
                    "Delete directory recursively. Args: path",
                ),
                ("copy_file", self.fm.copy_file, "Copy file. Args: src, dst"),
                ("move_file", self.fm.move_file, "Move/rename file. Args: src, dst"),
                ("file_info", self.fm.file_info, "Get metadata of file. Args: path"),
                (
                    "search_files",
                    self.fm.search_files,
                    "Search files by name pattern. Args: path, pattern",
                ),
                (
                    "grep_file",
                    self.fm.grep_file,
                    "Search text in file. Args: path, query",
                ),
                (
                    "grep_dir",
                    self.fm.grep_dir,
                    "Grep across directory. Args: path, query, pattern",
                ),
                (
                    "edit_file",
                    self.fm.edit_file,
                    "Replace text in file. Args: path, old_text, new_text",
                ),
                (
                    "edit_line",
                    self.fm.edit_line,
                    "Replace a specific line. Args: path, line_number, new_content",
                ),
                (
                    "insert_line",
                    self.fm.insert_line,
                    "Insert a line before line_number. Args: path, line_number, content",
                ),
                (
                    "zip_files",
                    self.fm.zip_files,
                    "Zip files/dirs. Args: output_path, *sources",
                ),
                ("unzip_file", self.fm.unzip_file, "Unzip archive. Args: path, dest"),
                (
                    "file_exists",
                    self.fm.file_exists,
                    "Check if path exists. Args: path",
                ),
                (
                    "file_hash",
                    self.fm.file_hash,
                    "Compute file hash. Args: path, algorithm (optional)",
                ),
                (
                    "read_json",
                    self.fm.read_json,
                    "Read and parse JSON file. Args: path",
                ),
                (
                    "write_json",
                    self.fm.write_json,
                    "Write JSON file. Args: path, data (JSON string)",
                ),
                ("read_csv", self.fm.read_csv, "Read CSV as text table. Args: path"),
                (
                    "write_csv",
                    self.fm.write_csv,
                    "Write CSV (JSON array of arrays). Args: path, data",
                ),
                (
                    "diff_files",
                    self.fm.diff_files,
                    "Show diff between two files. Args: path1, path2",
                ),
                (
                    "tree",
                    self.fm.tree,
                    "Show directory tree. Args: path, max_depth (optional)",
                ),
                ("count_lines", self.fm.count_lines, "Count lines in file. Args: path"),
                ("word_count", self.fm.word_count, "Word/line/char count. Args: path"),
                (
                    "touch",
                    self.fm.touch,
                    "Create empty file or update timestamps. Args: path",
                ),
                (
                    "find_large_files",
                    self.fm.find_large_files,
                    "Find large files. Args: path, min_mb (optional)",
                ),
                (
                    "replace_in_dir",
                    self.fm.replace_in_dir,
                    "Bulk replace text. Args: path, pattern, old_text, new_text",
                ),
                ("get_cwd", self.fm.get_cwd, "Get current working directory."),
                (
                    "set_cwd",
                    self.fm.set_cwd,
                    "Change current working directory. Args: path",
                ),
            ]
            for name, fn, desc in file_tools:
                self._reg(name, fn, desc, category="Files")

        if self.tools_cfg.get("terminal", True):
            terminal_tools = [
                (
                    "run_command",
                    self.term.run_command,
                    "Run shell command. Args: command",
                ),
                (
                    "run_script",
                    self.term.run_script,
                    "Run a script file. Args: path, interpreter (optional)",
                ),
                (
                    "run_python",
                    self.term.run_python,
                    "Run Python code string. Args: code",
                ),
                (
                    "run_powershell",
                    self.term.run_powershell,
                    "Run PowerShell command. Args: command",
                ),
                ("get_env", self.term.get_env, "Get env variable. Args: name"),
                (
                    "set_env",
                    self.term.set_env,
                    "Set env variable (session). Args: name, value",
                ),
                (
                    "list_env",
                    self.term.list_env,
                    "List env variables. Args: filter_str (optional)",
                ),
                ("unset_env", self.term.unset_env, "Unset env variable. Args: name"),
                ("which", self.term.which, "Find executable path. Args: name"),
                (
                    "special_paths",
                    self.term.special_paths,
                    "List common user/system paths.",
                ),
                (
                    "locate_path",
                    self.term.locate_path,
                    "Search common locations for a file or directory. Args: name, roots (optional)",
                ),
                (
                    "self_pid",
                    self.term.self_pid,
                    "Get this agent process PID. Args: none",
                ),
                (
                    "self_process_info",
                    self.term.self_process_info,
                    "Get this agent process details (PID/name/path/cmdline best-effort). Args: none",
                ),
                (
                    "process_list",
                    self.term.process_list,
                    "List running processes. Args: filter_str (optional)",
                ),
                (
                    "process_list_detailed",
                    self.term.process_list_detailed,
                    "Detailed process list (includes command line best-effort). Args: filter_str (optional)",
                ),
                (
                    "kill_process",
                    self.term.kill_process,
                    "Kill process by PID. Args: pid",
                ),
                (
                    "kill_process_by_name",
                    self.term.kill_process_by_name,
                    "Kill process by image name (e.g., spotify.exe). Args: image_name",
                ),
                (
                    "start_background",
                    self.term.start_background,
                    "Start command in background. Args: command",
                ),
                (
                    "launch_application",
                    self.term.launch_application,
                    "Launch desktop application. Args: app_name, arguments (optional)",
                ),
                (
                    "find_app",
                    self.term.find_app,
                    "Find an app executable path (dynamic: PATH/registry/Start Menu). Args: app_name",
                ),
                (
                    "open_app",
                    self.term.open_app,
                    "Open an app (dynamic discovery + launch). Args: app_name, arguments(optional)",
                ),
                (
                    "open_spotify_search",
                    self.term.open_spotify_search,
                    "Open Spotify search in browser/app. Args: query",
                ),
                (
                    "wait_for_port",
                    self.term.wait_for_port,
                    "Wait for port to open. Args: port, host, timeout",
                ),
                ("system_info", self.term.system_info, "Get OS/hardware info."),
                (
                    "disk_usage",
                    self.term.disk_usage,
                    "Disk usage. Args: path (optional)",
                ),
                ("cpu_usage", self.term.cpu_usage, "CPU usage snapshot."),
                ("memory_usage", self.term.memory_usage, "Memory usage."),
                (
                    "system_health",
                    self.term.system_health,
                    "Detailed report on system CPU, Memory, and Disk health, including agent process stats.",
                ),
                ("uptime", self.term.uptime, "System uptime."),
                (
                    "set_wallpaper",
                    self.term.set_wallpaper,
                    "Set Windows desktop wallpaper to local image. Args: path",
                ),
                (
                    "window_list",
                    self.term.window_list,
                    "List windows with titles (Windows). Args: filter_str(optional)",
                ),
                (
                    "window_focus",
                    self.term.window_focus,
                    "Focus a window by title substring (Windows). Args: title",
                ),
                (
                    "window_close",
                    self.term.window_close,
                    "Close a window by title substring (Windows). Args: title",
                ),
                (
                    "network_interfaces",
                    self.term.network_interfaces,
                    "List network interfaces.",
                ),
                ("ping", self.term.ping, "Ping a host. Args: host, count (optional)"),
                ("traceroute", self.term.traceroute, "Traceroute to host. Args: host"),
                ("netstat", self.term.netstat, "Show active network connections."),
                (
                    "pip_install",
                    self.term.pip_install,
                    "Install Python package. Args: package",
                ),
                ("pip_list", self.term.pip_list, "List installed packages."),
                (
                    "npm_install",
                    self.term.npm_install,
                    "Install npm package. Args: package, global_flag (optional)",
                ),
                ("git", self.term.git, "Run git command. Args: *args"),
                (
                    "git_status",
                    self.term.git_status,
                    "Git status. Args: path (optional)",
                ),
                ("git_log", self.term.git_log, "Git log. Args: path, n (optional)"),
                (
                    "open_file",
                    self.term.open_file,
                    "Open file with default application. Args: path",
                ),
                (
                    "open_url",
                    self.term.open_url,
                    "Open URL in default browser. Args: url",
                ),
                (
                    "open_url_verified",
                    self.term.open_url_verified,
                    "Open URL and verify a browser process exists (best-effort). Args: url",
                ),
                ("clipboard_get", self.term.clipboard_get, "Get clipboard text."),
                (
                    "clipboard_set",
                    self.term.clipboard_set,
                    "Set clipboard text. Args: text",
                ),
                (
                    "open_whatsapp_web",
                    self.term.open_whatsapp_web,
                    "Open WhatsApp Web.",
                ),
                (
                    "open_whatsapp_chat",
                    self.term.open_whatsapp_chat,
                    "Open WhatsApp chat by phone. Args: phone, message(optional)",
                ),
                (
                    "open_telegram",
                    self.term.open_telegram,
                    "Open Telegram web or username. Args: target(optional)",
                ),
                (
                    "open_instagram_profile",
                    self.term.open_instagram_profile,
                    "Open Instagram profile. Args: username",
                ),
                (
                    "open_x_profile",
                    self.term.open_x_profile,
                    "Open X/Twitter profile. Args: username",
                ),
                (
                    "open_facebook_profile",
                    self.term.open_facebook_profile,
                    "Open Facebook profile or URL. Args: handle_or_url",
                ),
                ("open_discord", self.term.open_discord, "Open Discord in browser."),
                (
                    "compose_email",
                    self.term.compose_email,
                    "Compose an email and open it in the default mail client. Args: to, subject(optional), body(optional), cc(optional), bcc(optional)",
                ),
                (
                    "open_google_search",
                    self.term.open_google_search,
                    "Open Google search. Args: query",
                ),
                (
                    "open_google_maps",
                    self.term.open_google_maps,
                    "Open Google Maps search. Args: query",
                ),
                (
                    "open_youtube_search",
                    self.term.open_youtube_search,
                    "Open YouTube search. Args: query",
                ),
                (
                    "open_github_search",
                    self.term.open_github_search,
                    "Open GitHub search. Args: query",
                ),
                (
                    "open_stackoverflow_search",
                    self.term.open_stackoverflow_search,
                    "Open StackOverflow search. Args: query",
                ),
                (
                    "eventlog_query",
                    self.term.eventlog_query,
                    "Query Windows Event Log. Args: log_name(optional), query(optional), n(optional)",
                ),
                (
                    "installed_apps",
                    self.term.installed_apps,
                    "List installed apps (Windows). Args: filter_str(optional)",
                ),
                (
                    "service_list",
                    self.term.service_list,
                    "List services. Args: filter_str(optional)",
                ),
                (
                    "service_status",
                    self.term.service_status,
                    "Service status. Args: name",
                ),
                (
                    "service_start",
                    self.term.service_start,
                    "Start service (guarded). Args: name",
                ),
                (
                    "service_stop",
                    self.term.service_stop,
                    "Stop service (guarded). Args: name",
                ),
                (
                    "scheduled_tasks_list",
                    self.term.scheduled_tasks_list,
                    "List scheduled tasks (Windows). Args: filter_str(optional)",
                ),
                (
                    "scheduled_task_run",
                    self.term.scheduled_task_run,
                    "Run scheduled task (Windows). Args: task_name",
                ),
                (
                    "scheduled_task_create_daily",
                    self.term.scheduled_task_create_daily,
                    "Create daily scheduled task (guarded). Args: task_name, command, time_hhmm(optional)",
                ),
                (
                    "tools_count",
                    self.tools_count,
                    "Count all registered tools (authoritative). Args: none",
                ),
                (
                    "tools_list",
                    self.tools_list,
                    "List all registered tools (authoritative). Args: none",
                ),
                (
                    "memory_search",
                    self.memory_search,
                    "Search session memory text. Args: query, limit(optional)",
                ),
                (
                    "download_smart",
                    self.download_smart,
                    "Download with retries (curl->powershell->web) + validation. Args: url, dest_path",
                ),
                # ── Media & Audio controls ────────────────────────────────────────────
                (
                    "media_play_pause",
                    self.term.media_play_pause,
                    "Toggle play/pause for the active media player.",
                ),
                ("media_play", self.term.media_play, "Resume/start media playback."),
                (
                    "media_pause",
                    self.term.media_pause,
                    "Pause the active media player.",
                ),
                ("media_stop", self.term.media_stop, "Stop media playback."),
                ("media_next", self.term.media_next, "Skip to the next track."),
                (
                    "media_previous",
                    self.term.media_previous,
                    "Go to the previous track.",
                ),
                (
                    "media_status",
                    self.term.media_status,
                    "Get currently playing track info and playback status.",
                ),
                (
                    "media_seek",
                    self.term.media_seek,
                    "Seek forward/backward by N seconds. Args: seconds (+/-)",
                ),
                (
                    "volume_set",
                    self.term.volume_set,
                    "Set system master volume 0-100. Args: level",
                ),
                (
                    "volume_up",
                    self.term.volume_up,
                    "Raise system volume by step% (default 10). Args: step(optional)",
                ),
                (
                    "volume_down",
                    self.term.volume_down,
                    "Lower system volume by step% (default 10). Args: step(optional)",
                ),
                ("volume_mute", self.term.volume_mute, "Toggle system mute on/off."),
                (
                    "volume_get",
                    self.term.volume_get,
                    "Get current system master volume level.",
                ),
                # ── Keyboard & Mouse input ────────────────────────────────────────────
                (
                    "hotkey",
                    self.term.hotkey,
                    "Send a keyboard shortcut/hotkey. Args: keys (e.g. ctrl+c, alt+f4, win+d), window(optional)",
                ),
                (
                    "press_key",
                    self.term.press_key,
                    "Press a single key N times. Args: key (enter/tab/esc/f5/up/etc), repeat(optional)",
                ),
                (
                    "type_text",
                    self.term.type_text,
                    "Type text as keyboard input. Args: text, delay_ms(optional)",
                ),
                (
                    "key_down",
                    self.term.key_down,
                    "Hold a key down. Args: key (shift/ctrl/alt/etc)",
                ),
                ("key_up", self.term.key_up, "Release a held key. Args: key"),
                (
                    "mouse_click",
                    self.term.mouse_click,
                    "Simulate mouse click. Args: button(left/right/middle), x(optional), y(optional)",
                ),
                (
                    "mouse_move",
                    self.term.mouse_move,
                    "Move mouse cursor to coordinates. Args: x, y",
                ),
                (
                    "mouse_scroll",
                    self.term.mouse_scroll,
                    "Scroll mouse wheel. Args: direction(up/down), clicks(optional)",
                ),
                (
                    "focus_window_and_hotkey",
                    self.term.focus_window_and_hotkey,
                    "Focus a window then send a hotkey. Args: window, keys",
                ),
                (
                    "hotkey_list",
                    self.term.hotkey_list,
                    "List all custom named shortcut aliases.",
                ),
                (
                    "hotkey_set",
                    self.term.hotkey_set,
                    "Define/update a custom named shortcut (session). Args: name, keys",
                ),
                (
                    "hotkey_delete",
                    self.term.hotkey_delete,
                    "Remove a custom named shortcut. Args: name",
                ),
            ]
            for name, fn, desc in terminal_tools:
                self._reg(name, fn, desc, category="Terminal")

            # Bulk register URL presets as individual tools. This makes the agent "feel" much more capable
            # without bloating the codebase with hundreds of tiny functions.
            for preset in load_url_presets(self.cfg):
                tool = preset.get("tool", "")
                mode = preset.get("mode", "direct")
                url = preset.get("url", "")
                desc = preset.get("desc", "Open preset URL.")
                if not tool or not url:
                    continue

                if mode == "direct":

                    def _mk_direct(u):
                        def _fn():
                            return self.term.open_url(u)

                        return _fn

                    self._reg(tool, _mk_direct(url), desc)
                elif mode in ("query", "path"):

                    def _mk_value(u):
                        # Many LLMs prefer using argument names like "query" or "username" instead of "value".
                        # Accept a few aliases so JSON ACTION args don't fail with missing required parameters.
                        def _fn(
                            value: str = "",
                            query: str = "",
                            url: str = "",
                            username: str = "",
                            phone: str = "",
                            message: str = "",
                            **_: object,
                        ):
                            raw = (
                                value
                                or query
                                or url
                                or username
                                or phone
                                or message
                                or ""
                            )
                            v = urllib.parse.quote((raw or "").strip())
                            return self.term.open_url(u.format(value=v))

                        return _fn

                    self._reg(tool, _mk_value(url), desc)

        if self.tools_cfg.get("web", True):
            web_tools = [
                (
                    "web_search",
                    self.web.search,
                    "Search the web. Args: query, num_results (optional)",
                ),
                (
                    "search_news",
                    self.web.search_news,
                    "Search news. Args: query, num_results (optional)",
                ),
                (
                    "fetch_url",
                    self.web.fetch_url,
                    "Fetch webpage raw content. Args: url",
                ),
                (
                    "get_page_text",
                    self.web.get_page_text,
                    "Extract readable text from webpage. Args: url",
                ),
                (
                    "get_page_links",
                    self.web.get_page_links,
                    "Extract links from webpage. Args: url",
                ),
                (
                    "get_page_images",
                    self.web.get_page_images,
                    "Extract image URLs from webpage. Args: url",
                ),
                (
                    "web_pick_best_link",
                    web_pick_best_link,
                    "Search then extract best link from results page. Args: query, domain_hint(optional)",
                ),
                (
                    "download_file",
                    self.web.download_file,
                    "Download file from URL. Args: url, dest_path",
                ),
                (
                    "get_json_api",
                    self.web.get_json_api,
                    "GET a JSON API. Args: url, headers (optional JSON)",
                ),
                (
                    "post_json_api",
                    self.web.post_json_api,
                    "POST JSON to API. Args: url, body (JSON), headers (optional)",
                ),
                (
                    "put_json_api",
                    self.web.put_json_api,
                    "PUT JSON to API. Args: url, body (JSON), headers (optional)",
                ),
                (
                    "delete_api",
                    self.web.delete_api,
                    "DELETE request. Args: url, headers (optional)",
                ),
                (
                    "graphql_query",
                    self.web.graphql_query,
                    "GraphQL query. Args: url, query, variables (optional)",
                ),
                (
                    "check_url",
                    self.web.check_url,
                    "Check if URL is reachable. Args: url",
                ),
                ("http_headers", self.web.http_headers, "Get HTTP headers. Args: url"),
                (
                    "get_ssl_info",
                    self.web.get_ssl_info,
                    "Get SSL certificate info. Args: hostname",
                ),
                ("whois_lookup", self.web.whois_lookup, "WHOIS lookup. Args: domain"),
                (
                    "resolve_dns",
                    self.web.resolve_dns,
                    "DNS lookup. Args: hostname, record_type (optional)",
                ),
                (
                    "get_ip_info",
                    self.web.get_ip_info,
                    "Get IP geolocation. Args: ip (optional)",
                ),
                (
                    "get_public_ip",
                    self.web.get_public_ip,
                    "Get public IP of this machine.",
                ),
                ("shorten_url", self.web.shorten_url, "Shorten a URL. Args: url"),
                (
                    "expand_url",
                    self.web.expand_url,
                    "Follow redirects to final URL. Args: url",
                ),
                (
                    "rss_feed",
                    self.web.rss_feed,
                    "Fetch and parse RSS feed. Args: url, num_items (optional)",
                ),
                (
                    "wayback_snapshot",
                    self.web.wayback_snapshot,
                    "Get Wayback Machine snapshot. Args: url",
                ),
                (
                    "scrape_table",
                    self.web.scrape_table,
                    "Scrape HTML table. Args: url, table_index (optional)",
                ),
                (
                    "find_spotify_track",
                    self.web.find_spotify_track,
                    "Find Spotify track link. Args: title, artist (optional)",
                ),
                (
                    "play_spotify_track",
                    self.web.play_spotify_track,
                    "Find and immediately play a song on Spotify. Args: title, artist (optional)",
                ),
                (
                    "find_youtube_video",
                    self.web.find_youtube_video,
                    "Find YouTube video link. Args: query, channel (optional)",
                ),
            ]
            for name, fn, desc in web_tools:
                self._reg(name, fn, desc, category="Web")

        if self.tools_cfg.get("browser", True):
            browser_tools = [
                # ── Session management ──────────────────────────────────────────────
                (
                    "browser_launch",
                    self.web.browser_launch,
                    "Launch a Playwright browser session. Args: browser(chromium/firefox/webkit), headless(true/false), user_data_dir(optional profile path)",
                ),
                (
                    "browser_close",
                    self.web.browser_close,
                    "Close the active Playwright browser session and free resources.",
                ),
                (
                    "browser_status",
                    self.web.browser_status,
                    "Show current browser session status (URL, title, tab count).",
                ),
                # ── Navigation ─────────────────────────────────────────────────────
                (
                    "browser_navigate",
                    self.web.browser_navigate,
                    "Navigate to a URL. Args: url, wait_until(load/domcontentloaded/networkidle)",
                ),
                (
                    "browser_go_back",
                    self.web.browser_go_back,
                    "Navigate back in browser history.",
                ),
                (
                    "browser_go_forward",
                    self.web.browser_go_forward,
                    "Navigate forward in browser history.",
                ),
                ("browser_reload", self.web.browser_reload, "Reload the current page."),
                (
                    "browser_new_tab",
                    self.web.browser_new_tab,
                    "Open a new browser tab. Args: url(optional)",
                ),
                # ── Page reading ────────────────────────────────────────────────────
                (
                    "browser_get_url",
                    self.web.browser_get_url,
                    "Get the current page URL.",
                ),
                (
                    "browser_get_title",
                    self.web.browser_get_title,
                    "Get the current page title.",
                ),
                (
                    "browser_get_text",
                    self.web.browser_get_text,
                    "Get all visible text from the current page (JS innerText, works on SPAs/Gmail).",
                ),
                (
                    "browser_get_html",
                    self.web.browser_get_html,
                    "Get the full outer HTML of the current page (capped at 50k chars).",
                ),
                (
                    "browser_get_element_text",
                    self.web.browser_get_element_text,
                    "Get text of a specific element. Args: selector",
                ),
                (
                    "browser_get_elements",
                    self.web.browser_get_elements,
                    "Find all elements matching a CSS/XPath selector. Args: selector",
                ),
                (
                    "browser_get_links",
                    self.web.browser_get_links,
                    "Extract all hyperlinks from the current page (text → href).",
                ),
                (
                    "browser_get_inputs",
                    self.web.browser_get_inputs,
                    "List all input fields (name, type, value) on the current page.",
                ),
                # ── Interactions ────────────────────────────────────────────────────
                (
                    "browser_click",
                    self.web.browser_click,
                    "Click an element. Args: selector",
                ),
                (
                    "browser_fill",
                    self.web.browser_fill,
                    "Fill an input field (replaces existing content). Args: selector, value",
                ),
                (
                    "browser_type",
                    self.web.browser_type,
                    "Type text char-by-char into an element (simulates keystrokes). Args: selector, text, delay_ms(optional)",
                ),
                (
                    "browser_select",
                    self.web.browser_select,
                    "Select a <select> dropdown option. Args: selector, value",
                ),
                (
                    "browser_check",
                    self.web.browser_check,
                    "Check or uncheck a checkbox. Args: selector, checked(true/false)",
                ),
                (
                    "browser_press_key",
                    self.web.browser_press_key,
                    "Press a keyboard key or shortcut in the browser. Args: key (e.g. Enter, Control+a, Tab)",
                ),
                (
                    "browser_scroll",
                    self.web.browser_scroll,
                    "Scroll the page. Args: direction(up/down/top/bottom), amount(px, optional)",
                ),
                (
                    "browser_wait_for",
                    self.web.browser_wait_for,
                    "Wait for an element to appear. Args: selector, timeout_ms(optional)",
                ),
                # ── JS execution ────────────────────────────────────────────────────
                (
                    "browser_execute_js",
                    self.web.browser_execute_js,
                    "Execute JavaScript in the page context. Args: code",
                ),
                # ── Screenshot ──────────────────────────────────────────────────────
                (
                    "browser_screenshot",
                    self.web.browser_screenshot,
                    "Save a screenshot of the current page. Args: path(optional), full_page(true/false)",
                ),
                # ── Cookies ─────────────────────────────────────────────────────────
                (
                    "browser_get_cookies",
                    self.web.browser_get_cookies,
                    "Get all cookies in the current browser context.",
                ),
                (
                    "browser_set_cookie",
                    self.web.browser_set_cookie,
                    "Set a cookie. Args: name, value, domain(optional), path(optional)",
                ),
                (
                    "browser_clear_cookies",
                    self.web.browser_clear_cookies,
                    "Clear all cookies in the current browser context.",
                ),
            ]
            for name, fn, desc in browser_tools:
                self._reg(name, fn, desc)

        if self.tools_cfg.get("notifications", True):
            notification_tools = [
                (
                    "send_notification",
                    self.ui.send_notification,
                    "Send desktop alert. Args: title, message",
                ),
                (
                    "show_popup",
                    self.ui.show_popup,
                    "Show popup message box. Args: title, message",
                ),
                ("speak", self.ui.speak, "Text-to-speech. Args: text"),
                ("alert", self.ui.alert, "Notify and speak. Args: message"),
                (
                    "take_screenshot",
                    self.screen.take_screenshot,
                    "Take screenshot. Args: name (optional)",
                ),
                (
                    "list_windows",
                    self.screen.list_windows,
                    "List visible application windows. Args: filter_str (optional)",
                ),
                (
                    "focus_app",
                    self.screen.focus_app,
                    "Focus specific app window. Args: app_name",
                ),
                ("minimize_all", self.screen.minimize_all, "Minimize all windows."),
                (
                    "minimize_app",
                    self.screen.minimize_app,
                    "Minimize specific app. Args: app_name",
                ),
                (
                    "maximize_app",
                    self.screen.maximize_app,
                    "Maximize specific app. Args: app_name",
                ),
                (
                    "set_wallpaper",
                    self.ui.set_wallpaper,
                    "Set desktop wallpaper. Args: image_path",
                ),
                # ── Browser reading ───────────────────────────────────────────────────
                (
                    "get_browser_url",
                    self.term.get_browser_url,
                    "Get the current URL shown in the active browser tab. Args: browser(optional, e.g. 'brave')",
                ),
                (
                    "browser_read_page_text",
                    self.term.browser_read_page_text,
                    "Read all visible text from the active browser tab (Ctrl+A+C). Args: browser(optional)",
                ),
                (
                    "browser_read_selection",
                    self.term.browser_read_selection,
                    "Read the currently selected/highlighted text in the browser. Args: browser(optional)",
                ),
            ]
            for name, fn, desc in notification_tools:
                self._reg(name, fn, desc)

        if self.tools_cfg.get("calculator", True):
            self._reg(
                "calculate",
                self._calculate,
                "Evaluate math expression. Args: expression",
            )
        if self.tools_cfg.get("datetime_tool", True):
            self._reg("current_datetime", self._now, "Get current date/time.")
            self._reg("timestamp", self._timestamp, "Get unix timestamp.")
        if self.tools_cfg.get("note_pad", True):
            self._reg(
                "note_add",
                self._note_add,
                "Add a note to the general notepad. Args: text",
            )
            self._reg("note_list", self._note_list, "List all general notes.")
            self._reg("note_clear", self._note_clear, "Clear general notepad.")

        if self.tools_cfg.get("canvas", True):
            self._reg(
                "canvas_set",
                self._canvas_set,
                "Overwrite the Thinking Canvas with a new draft. Use this for complex code, regex, or plans. Args: content",
            )
            self._reg(
                "canvas_append",
                self._canvas_append,
                "Append text to the current Thinking Canvas. Args: content",
            )
            self._reg(
                "canvas_view",
                self._canvas_view,
                "View the current contents of the Thinking Canvas.",
            )
            self._reg("canvas_clear", self._canvas_clear, "Clear the Thinking Canvas.")

        # Preferences backed by SQLite memory (optional)
        self._reg(
            "pref_set", self._pref_set, "Set a stored preference. Args: key, value"
        )
        self._reg("pref_list", self._pref_list, "List stored preferences.")

    def _pref_set(self, key: str, value: str) -> str:
        if self._memory is not None and hasattr(self._memory, "set_preference"):
            self._memory.set_preference(key, value)
            return "OK"
        return (
            "Error: preferences storage not available (enable memory.backend=sqlite)."
        )

    def _pref_list(self) -> str:
        if self._memory is not None and hasattr(self._memory, "get_preferences"):
            prefs = self._memory.get_preferences()
            if not prefs:
                return "(no preferences)"
            return "\n".join(f"{k}={v}" for k, v in prefs.items())
        return (
            "Error: preferences storage not available (enable memory.backend=sqlite)."
        )

    def _load_plugins(self):
        """Scan tools/plugins/ (and subdirectories) for any .py files and register functions with @tool."""
        plugin_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "tools", "plugins"
        )
        if not os.path.isdir(plugin_dir):
            return

        for root, _, files in os.walk(plugin_dir):
            for filename in files:
                if filename.endswith(".py") and filename != "__init__.py":
                    module_name = filename[:-3]
                    file_path = os.path.join(root, filename)

                    try:
                        spec = importlib.util.spec_from_file_location(
                            module_name, file_path
                        )
                        if spec and spec.loader:
                            module = importlib.util.module_from_spec(spec)
                            sys.modules[module_name] = module
                            spec.loader.exec_module(module)

                            # Find all decorated functions
                            for attr_name in dir(module):
                                attr = getattr(module, attr_name)
                                if callable(attr) and hasattr(attr, "_is_tool"):
                                    name = getattr(attr, "_tool_name")
                                    desc = getattr(attr, "_tool_desc")
                                    category = getattr(attr, "_tool_category", "Plugins")
                                    self._reg(name, attr, desc, category=category)
                    except Exception as e:
                        print(f"  [PLUGIN ERROR] Failed to load {filename}: {e}")

    def _reg(self, name, fn, desc, category="General"):
        self.registry[name] = {"fn": fn, "desc": desc, "category": category}

    def _calculate(self, expression: str) -> str:

        allowed = {
            key: getattr(math, key) for key in dir(math) if not key.startswith("_")
        }
        allowed.update({"abs": abs, "round": round, "min": min, "max": max, "sum": sum})
        operators = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.FloorDiv: operator.floordiv,
            ast.Mod: operator.mod,
            ast.Pow: operator.pow,
            ast.USub: operator.neg,
            ast.UAdd: operator.pos,
        }

        def evaluate(node):
            if isinstance(node, ast.Expression):
                return evaluate(node.body)
            if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
                return node.value
            if isinstance(node, ast.BinOp) and type(node.op) in operators:
                return operators[type(node.op)](
                    evaluate(node.left), evaluate(node.right)
                )
            if isinstance(node, ast.UnaryOp) and type(node.op) in operators:
                return operators[type(node.op)](evaluate(node.operand))
            if isinstance(node, ast.Name) and node.id in allowed:
                return allowed[node.id]
            if isinstance(node, ast.Call):
                fn = evaluate(node.func)
                if fn not in allowed.values():
                    raise ValueError("Unsupported function")
                return fn(*(evaluate(arg) for arg in node.args))
            raise ValueError("Unsupported expression")

        try:
            return str(evaluate(ast.parse(expression, mode="eval")))
        except Exception as exc:
            return f"Error: {exc}"

    def _now(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _timestamp(self) -> str:
        return str(int(time.time()))

    def _note_add(self, text: str) -> str:
        self._notepad.append(f"[{self._now()}] {text}")
        return f"Note saved. Total notes: {len(self._notepad)}"

    def _note_list(self) -> str:
        if not self._notepad:
            return "Notepad is empty."
        return "\n".join(f"{i + 1}. {note}" for i, note in enumerate(self._notepad))

    def _note_clear(self) -> str:
        self._notepad.clear()
        return "Notepad cleared."

    def _canvas_set(self, content: str) -> str:
        self._canvas = str(content)
        return "Canvas updated."

    def _canvas_append(self, content: str) -> str:
        self._canvas += f"\n{content}"
        return "Canvas appended."

    def _canvas_view(self) -> str:
        if not self._canvas:
            return "Canvas is empty."
        return self._canvas

    def _canvas_clear(self) -> str:
        self._canvas = ""
        return "Canvas cleared."

    def tools_count(self) -> str:
        """Return the authoritative count of currently registered tools."""
        return str(len(self.registry))

    def tools_list(self) -> str:
        """Return the authoritative list of currently registered tools (one per line)."""
        return "\n".join(sorted(self.registry.keys()))

    def memory_search(self, query: str, limit: int = 10) -> str:
        """Search recent conversation memory for a substring (backend-agnostic)."""
        q = (query or "").strip().lower()
        if not q:
            return "Error: query required."
        try:
            msgs = []
            if self._memory and hasattr(self._memory, "get_messages"):
                msgs = self._memory.get_messages()
            hits = []
            for m in msgs or []:
                role = (m.get("role") or "").upper()
                content = m.get("content") or ""
                if q in content.lower():
                    preview = content.replace("\n", " ")
                    if len(preview) > 240:
                        preview = preview[:240] + "..."
                    hits.append(f"{role}: {preview}")
            if not hits:
                return "No matches."
            return "\n".join(hits[-int(limit) :])
        except Exception as e:
            return f"Error: {type(e).__name__}: {e}"

    def download_smart(self, url: str, dest_path: str) -> str:
        """Download with retries/fallbacks and post-checks.

        Strategy:
        1) curl (fast, reliable on Windows 10+)
        2) PowerShell Invoke-WebRequest
        3) built-in web.download_file
        Always validates dest exists and size > 0.
        """
        import os

        u = (url or "").strip()
        dst = (dest_path or "").strip()
        if not u or not dst:
            return "Error: url and dest_path required."
        # Resolve relative paths into workspace.
        if not os.path.isabs(dst):
            ws = self.cfg.get("agent", {}).get("workspace", DEFAULT_WORKSPACE)
            dst = os.path.join(ws, dst)
        try:
            os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
        except Exception:
            pass

        attempts = []

        # 1) curl
        try:
            curl_timeout = self.cfg.get("timeouts", {}).get("download_curl", 120)
            out = self.term.run_command(
                f'curl -L -o "{dst}" "{u}"', timeout=curl_timeout
            )
            attempts.append("curl")
            if os.path.exists(dst) and os.path.getsize(dst) > 0:
                return (
                    out
                    + f"\nVALIDATION: downloaded via curl (size={os.path.getsize(dst)})"
                )
        except Exception:
            pass

        # 2) PowerShell
        try:
            ps_timeout = self.cfg.get("timeouts", {}).get("download_powershell", 180)
            out = self.term.run_powershell(
                f"Invoke-WebRequest -Uri '{u}' -OutFile '{dst}'", timeout=ps_timeout
            )
            attempts.append("powershell")
            if os.path.exists(dst) and os.path.getsize(dst) > 0:
                return (
                    out
                    + f"\nVALIDATION: downloaded via powershell (size={os.path.getsize(dst)})"
                )
        except Exception:
            pass

        # 3) WebTools
        try:
            out = self.web.download_file(u, dst)
            attempts.append("web.download_file")
            if os.path.exists(dst) and os.path.getsize(dst) > 0:
                return (
                    out
                    + f"\nVALIDATION: downloaded via web.download_file (size={os.path.getsize(dst)})"
                )
            return out + "\nVALIDATION: download failed (file missing/empty)"
        except Exception as e:
            return f"Error: download failed after {attempts}: {type(e).__name__}: {e}"

    def call(self, name: str, args) -> str:
        if name not in self.registry:
            available = ", ".join(list(self.registry.keys())[:15])
            return f"Unknown tool: '{name}'. Available: {available}..."

        # ── Security Guardrails & Shadow Mode ─────────────────────────────────
        write_tools = {
            "write_file",
            "append_file",
            "delete_file",
            "create_dir",
            "delete_dir",
            "copy_file",
            "move_file",
            "edit_file",
            "edit_line",
            "insert_line",
            "replace_in_dir",
            "write_json",
            "write_csv",
            "touch",
            "run_command",
            "run_powershell",
            "run_script",
            "run_python",
            "pip_install",
            "npm_install",
            "git",
            "kill_process",
            "kill_process_by_name",
            "start_background",
            "hotkey",
            "press_key",
            "type_text",
            "mouse_click",
            "mouse_move",
        }

        # Shadow Mode Interception
        if self.shadow_mode and name in write_tools:
            return f"[SHADOW MODE] Dry run: would have executed '{name}' with args: {args}. Result simulated as SUCCESS."

        # ── Universal Path Guardrails ─────────────────────────────────────────
        # Automatically protect any argument that looks like a path
        path_keys = {
            "path",
            "src",
            "dst",
            "dest_path",
            "filename",
            "output_path",
            "directory",
        }
        read_only_tools = {
            "read_file",
            "list_dir",
            "file_info",
            "grep_file",
            "grep_dir",
            "read_json",
            "read_csv",
            "tree",
            "count_lines",
            "word_count",
            "file_exists",
            "file_hash",
        }

        if isinstance(args, dict):
            for key, val in args.items():
                if key.lower() in path_keys:
                    op = "read" if name in read_only_tools else "write"
                    allowed, msg = self.guard.check_path(str(val), operation=op)
                    if not allowed:
                        if msg == "HITM_REQUIRED":
                            if not self.guard.ask_human(str(val), name):
                                return f"SECURITY POLICY: The user has explicitly DENIED the '{name}' action on '{val}'. Do not attempt this action again or try to bypass this restriction."
                        else:
                            return msg
        elif isinstance(args, list) and len(args) > 0:
            # Fallback for positional args (assume first arg might be a path if tool is file-related)
            if any(
                t in name for t in ["file", "dir", "path", "read", "write", "delete"]
            ):
                op = "read" if name in read_only_tools else "write"
                allowed, msg = self.guard.check_path(str(args[0]), operation=op)
                if not allowed:
                    if msg == "HITM_REQUIRED":
                        if not self.guard.ask_human(str(args[0]), name):
                            return f"SECURITY POLICY: The user has explicitly DENIED the '{name}' action on '{args[0]}'. Do not attempt this action again or try to bypass this restriction."
                    else:
                        return msg
        # ──────────────────────────────────────────────────────────────────────

        try:
            fn = self.registry[name]["fn"]
            sig = inspect.signature(fn)
            params = [
                param
                for param in sig.parameters.values()
                if param.kind in (param.POSITIONAL_OR_KEYWORD, param.POSITIONAL_ONLY)
            ]

            # JSON/dict args (ACTION: {"tool": "...", "args": {...}})
            if isinstance(args, dict):
                kwargs = {}
                for p in params:
                    if p.name in args:
                        kwargs[p.name] = args[p.name]
                out = str(fn(**kwargs))
                note = ""
                if self.cfg.get("autonomy", {}).get("validate_results", True):
                    note = validate_tool(
                        name, args, out, workspace_root=self._workspace_root
                    )
                return f"{out}\n{note}".strip() if note else out

            clean_args = [
                arg
                for arg in (args or [])
                if (isinstance(arg, str) and arg.strip()) or not isinstance(arg, str)
            ]
            param_count = len(params)

            if len(clean_args) > param_count > 0:
                joined = "|".join(str(arg) for arg in clean_args[param_count - 1 :])
                clean_args = clean_args[: param_count - 1] + [joined]

            converted = []
            for arg in clean_args:
                if not isinstance(arg, str):
                    converted.append(arg)
                    continue
                stripped = arg.strip()
                if stripped.lstrip("-").isdigit():
                    converted.append(int(stripped))
                elif (
                    stripped.replace(".", "", 1).lstrip("-").isdigit()
                    and stripped.count(".") == 1
                ):
                    converted.append(float(stripped))
                else:
                    converted.append(stripped)

            out = str(fn(*converted)) if converted else str(fn())
            # Sentinel post‑logging
            if getattr(self, "sentinel", None):
                self.sentinel.log_action(name, args, out)
            note = ""
            if self.cfg.get("autonomy", {}).get("validate_results", True):
                note = validate_tool(
                    name, converted, out, workspace_root=self._workspace_root
                )
            return f"{out}\n{note}".strip() if note else out
        except TypeError as exc:
            return f"Tool argument error ({name}): {exc}\n  Expected: {self._get_signature(name)}"
        except PermissionError as exc:
            return f"Permission denied ({name}): {exc}"
        except FileNotFoundError as exc:
            return f"File not found ({name}): {exc}"
        except Exception as exc:
            return f"Tool error ({name}): {type(exc).__name__}: {exc}"

    def _get_signature(self, name: str) -> str:
        if name in self.registry:
            try:
                return str(inspect.signature(self.registry[name]["fn"]))
            except Exception:
                pass
        return "unknown"

    def get_symbol(self, name: str) -> str:
        name = name.lower()
        if any(
            token in name
            for token in ["file", "read", "write", "dir", "delete", "path", "move"]
        ):
            return "[F]"
        if any(
            token in name for token in ["run", "exec", "cmd", "ps", "terminal", "shell"]
        ):
            return "[T]"
        if any(
            token in name for token in ["web", "search", "get", "post", "url", "scrape"]
        ):
            return "[W]"
        if any(token in name for token in ["calc", "math", "sum", "average"]):
            return "[M]"
        if any(token in name for token in ["note", "pad", "list", "clear"]):
            return "[N]"
        if any(token in name for token in ["canvas"]):
            return "[C]"
        if any(token in name for token in ["sys", "cpu", "mem", "process", "service"]):
            return "[S]"
        if any(token in name for token in ["reg", "key", "value"]):
            return "[R]"
        return "[*]"

    def tool_descriptions(self) -> str:
        max_lines = int(self.cfg.get("prompts", {}).get("max_tool_descriptions", 140))
        
        # Group tools by category
        categories = {}
        for name, info in self.registry.items():
            cat = info.get("category", "General")
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(f"  {name}: {info['desc']}")

        # Build description string with headers
        output_lines = []
        total_count = 0
        
        # Prioritize core categories
        priority = ["Files", "Terminal", "Web", "Browser", "System"]
        sorted_cats = sorted(categories.keys(), key=lambda x: (priority.index(x) if x in priority else 999, x))
        
        for cat in sorted_cats:
            if total_count >= max_lines:
                break
            output_lines.append(f"\n[{cat.upper()}]:")
            for line in categories[cat]:
                if total_count >= max_lines:
                    break
                output_lines.append(line)
                total_count += 1
        
        if len(self.registry) > total_count:
            output_lines.append(
                f"\n  ... ({len(self.registry) - total_count} more tools available; use /tools to list)"
            )
            
        return "\n".join(output_lines).strip()
