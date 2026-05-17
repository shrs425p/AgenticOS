# AgenticOS: API & Tool Reference Guide

AgenticOS features a massive registry of over 180+ specialized tools. This document provides a high-level overview of the primary tool categories and their intended use cases.

---

## [FILE] Filesystem Tools (`Files` Category)

The foundation of the agent's ability to manipulate data.

| Tool | Arguments | Description |
| :--- | :--- | :--- |
| `read_file` | `path`, `start_line`, `num_lines` | Reads content with smart chunking support. |
| `write_file` | `path`, `content` | Atomic write to a file. |
| `edit_file` | `path`, `old_text`, `new_text` | Replaces specific substrings. |
| `grep_dir` | `path`, `query`, `pattern` | **Security Gated**: Recursive search for content inside files. |
| `search_files` | `path`, `pattern` | Finds files by name (e.g., `*.py`). |
| `find_large_files`| `path`, `min_mb` | **Security Gated**: Identifies disk bloat. |
| `file_info` | `path` | Returns size, mime-type, and modification time. |
| `zip_files` | `output_path`, `sources` | Archives multiple files/folders. |

---

## [SHELL] Terminal & OS Tools (`Terminal` Category)

Direct interaction with the Windows Operating System.

| Tool | Arguments | Description |
| :--- | :--- | :--- |
| `run_powershell` | `command` | Executes native PowerShell scripts. |
| `run_command` | `command` | Executes standard shell commands (CMD/Bash). |
| `process_list` | `filter_str` | Lists all running processes with PID and RAM. |
| `kill_process` | `pid` | Terminates a process (Subject to Guardrails). |
| `system_health` | `none` | Real-time CPU/RAM/Disk diagnostic. |
| `installed_apps` | `filter_str` | Lists software registered in the Windows Registry. |
| `service_list` | `filter_str` | Lists Windows services and their status. |
| `eventlog_query` | `log_name`, `query`, `n` | **Cross-Platform**: Queries Windows Event Logs or Unix journalctl logs. |
| `firewall_rules_list` | `filter_str` | **Security Audit**: Lists active Windows/Linux firewall rules. |
| `active_ports_list` | `none` | **Network Audit**: Lists active ports and binding PIDs (TCP/UDP). |
| `scheduled_task_create_daily` | `task_name`, `command`, `time_hhmm` | Registers a daily background scheduled task. |

---

## [WEB] Web & API Tools (`Web` Category)

Connecting the agent to global intelligence.

| Tool | Arguments | Description |
| :--- | :--- | :--- |
| `web_search` | `query`, `num_results`| High-speed search via Brave/Serper/Google. |
| `fetch_url` | `url` | Downloads raw webpage content. |
| `get_page_text` | `url` | Extracts readable text (removes HTML bloat). |
| `get_json_api` | `url`, `headers` | Fetches data from REST APIs. |
| `whois_lookup` | `domain` | Performs registration lookups. |
| `rss_feed` | `url` | Parses news feeds into structured lists. |
| `download_file` | `url`, `dest_path`, `timeout` | Download file from URL. |

---

## [BOT] Browser Automation (`Browser` Category)

Playwright-driven interactive web navigation.

| Tool | Arguments | Description |
| :--- | :--- | :--- |
| `get_browser_url` | `browser` | Get the current URL shown in the active browser tab. |
| `browser_read_page_text` | `browser` | Read all visible text from the active browser tab. |
| `browser_read_selection` | `browser` | Read the currently selected/highlighted text in the browser. |
| `open_url` | `url` | Open URL in default browser. |
| `window_focus` | `title` | Focus a window by title substring. |
| `window_close` | `title` | Close a window by title substring. |

---

## [MUSIC] Media & UI Control (`Media` Category)

Controlling the user environment and peripherals.

| Tool | Arguments | Description |
| :--- | :--- | :--- |
| `volume_set` | `level` (0-100) | Adjusts master system volume. |
| `media_play_pause`| `none` | Toggles active media playback. |
| `ocr_image` | `path` | Extracts text from a local image file (PNG, JPG). |
| `ocr_screen` | `none` | Captures the full screen and extracts all visible text. |
| `take_screenshot` | `name` | Saves a PNG of the screen to the workspace. |
| `list_windows` | `filter_str` | Lists all active application windows. |
| `set_wallpaper` | `path` | Updates the desktop background. |
| `hotkey` | `keys` | Sends global shortcuts (e.g., `win+d`). |
| `type_text` | `text`, `delay_ms` | Injects keyboard input into any focused app. |

---

## [LAUNCH] Performance Plugins (`Custom`)

Specialized tools added for the v2.0.0 Production hardening.

| Tool | Arguments | Description |
| :--- | :--- | :--- |
| `find_large_files` | `path`, `min_mb` | Find large files. |
| `plugin_health_check` | None | Run plugin health check. |
| `generate_session_summary` | None | Generates a daily session summary from logs. |

---

## [DOC] Using the Reference
This is a condensed list. For a full, live inventory of every tool available to your specific instance, type the following command into your terminal:

```powershell
/tools
```

This will output the documentation, argument schemas, and version numbers for all **180+ tools** currently registered in your system.

---

*Last Updated: 2026-05-13*
*Status: API Reference Complete*
