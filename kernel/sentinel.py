# Sentinel system for AgenticOs

"""Sentinel provides runtime monitoring and policy enforcement for tool usage.

Features:
- Loads a simple blocklist (tool names that are prohibited).
- Pre‑execution check that can abort a tool call with a clear error message.
- Post‑execution logging of every tool invocation to a workspace‑local log file.
- Optional callback hook for real‑time alerts (e.g., sending a desktop notification).
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, List, Optional


class Sentinel:
    def __init__(
        self,
        workspace: str,
        cfg_path: Optional[str] = None,
        alert_callback: Optional[Callable[[str], None]] = None,
    ):
        """Initialize the Sentinel.

        Args:
            workspace: Base workspace directory (used for the log file).
            cfg_path: Optional path to a JSON cfg file containing a "blocklist" key.
            alert_callback: Optional callable that receives an alert string (e.g., to display a toast).
        """
        self.workspace = Path(workspace).resolve()
        self.log_path = self.workspace / "sentinel.log"
        self.blocklist: List[str] = []
        self.alert_callback = alert_callback
        if cfg_path:
            self._load_cfg(cfg_path)
        else:
            # Default: empty blocklist
            self.blocklist = []
        # Ensure log file exists
        self.log_path.touch(exist_ok=True)

    def _load_cfg(self, cfg_path: str) -> None:
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                self.blocklist = [
                    str(item).strip().lower() for item in cfg.get("blocklist", [])
                ]
        except Exception as e:
            # If cfg cannot be read, treat as empty blocklist but record the issue
            self._write_log(f"[Sentinel] Failed to load cfg {cfg_path}: {e}")
            self.blocklist = []

    def pre_check(self, tool_name: str, args: Any) -> Optional[str]:
        """Check whether the tool is allowed. Return an error string if blocked, otherwise None."""
        if tool_name.lower() in self.blocklist:
            msg = f"Sentinel: Blocked execution of prohibited tool '{tool_name}'."
            self._write_log(msg)
            if self.alert_callback:
                self.alert_callback(msg)
            return msg
        return None

    def log_action(self, tool_name: str, args: Any, result: str) -> None:
        """Log a tool invocation with timestamp, arguments and result."""
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = {
            "timestamp": ts,
            "tool": tool_name,
            "args": args,
            "result": result,
        }
        line = json.dumps(entry, ensure_ascii=False)
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            # In a failure scenario we silently ignore to avoid breaking the main flow
            pass

    def _write_log(self, message: str) -> None:
        """Internal helper to append plain‑text messages to the log file."""
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(f"[{ts}] {message}\n")
        except Exception:
            pass
