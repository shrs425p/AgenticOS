"""
AgenticOs — session memory
Persistent short-term memory using JSON storage.
"""

import os
import json
from datetime import datetime
from pathlib import Path


class SessionMemory:
    def __init__(self, cfg: dict):
        self.max_messages = cfg.get("max_messages", 100)
        self.summarise_after = cfg.get("summarise_after", 80)

        workspace = cfg.get("workspace") or os.environ.get("AGENTICOS_WORKSPACE")
        if not workspace:
            workspace = Path(__file__).resolve().parent / "workspace"
        json_filename = cfg.get("json_filename", "memory.json")
        self.file_path = os.path.join(
            os.path.abspath(os.path.expanduser(str(workspace))), json_filename
        )

        self._messages: list[dict] = []
        self._created_at = datetime.now()
        self._turn_count = 0

        self._load()

    def _load(self):
        """Load memory from JSON file if it exists."""
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._messages = data.get("messages", [])
                    self._turn_count = data.get("turn_count", 0)
                    # We keep the original start time if available
                    if "created_at" in data:
                        try:
                            self._created_at = datetime.fromisoformat(
                                data["created_at"]
                            )
                        except ValueError:
                            pass
            except Exception as e:
                print(f"Warning: Failed to load memory.json: {e}")

    def _save(self):
        """Save current memory to JSON file."""
        try:
            data = {
                "messages": self._messages,
                "turn_count": self._turn_count,
                "created_at": self._created_at.isoformat(),
                "last_updated": datetime.now().isoformat(),
            }
            os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to save memory.json: {e}")

    def add(self, role: str, content: str):
        self._messages.append({"role": role, "content": content})
        if role == "user":
            self._turn_count += 1

        # Trim to keep within limits
        if len(self._messages) > self.max_messages:
            excess = len(self._messages) - self.max_messages
            self._messages = self._messages[excess:]

        self._save()

    def get_messages(self) -> list[dict]:
        return list(self._messages)

    def clear(self):
        """Physically delete the memory JSON file to ensure a total session wipe."""
        self._messages.clear()
        self._turn_count = 0
        if os.path.exists(self.file_path):
            try:
                os.remove(self.file_path)
                # Reset creation time for a truly fresh start next time
                self._created_at = datetime.now()
            except Exception as e:
                print(f"Warning: Could not physically delete {self.file_path}: {e}")

    def summary(self) -> str:
        uptime = datetime.now() - self._created_at
        mins, secs = divmod(int(uptime.total_seconds()), 60)
        return (
            f"  Messages : {len(self._messages)}\n"
            f"  Turns    : {self._turn_count}\n"
            f"  Session  : {mins}m {secs}s\n"
            f"  Storage  : {self.file_path}\n"
            f"  Started  : {self._created_at.strftime('%Y-%m-%d %H:%M:%S')}"
        )

    @property
    def turn_count(self) -> int:
        return self._turn_count
