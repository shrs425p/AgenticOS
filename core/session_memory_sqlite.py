"""SQLite-backed session memory.

Stores conversation messages per session in a local SQLite database inside the workspace.
This avoids unbounded JSON growth and makes history queries cheap.
"""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime
import re


def _now_iso() -> str:
    return datetime.now().isoformat(sep=" ", timespec="seconds")


def _default_db_path(workspace: str) -> str:
    return os.path.join(workspace, "memory.sqlite3")


@dataclass
class _Msg:
    role: str
    content: str
    created_at: str


class SqliteSessionMemory:
    def __init__(self, cfg: dict):
        self.cfg = cfg or {}
        self.workspace = self.cfg.get("workspace") or "workspace"
        self.max_messages = int(self.cfg.get("max_messages", 500))
        self.summarise_after = int(self.cfg.get("summarise_after", 200))
        self.redact_secrets = bool(self.cfg.get("redact_secrets", True))

        self.session_id = self.cfg.get("session_id") or datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )
        self.db_path = self.cfg.get("db_path") or _default_db_path(self.workspace)

        os.makedirs(self.workspace, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path, timeout=10, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute("PRAGMA synchronous=NORMAL;")
        self._init_schema()
        self._ensure_session_row()

    def _init_schema(self):
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
              session_id TEXT PRIMARY KEY,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              summary TEXT NOT NULL DEFAULT ''
            );
            """
        )
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS preferences (
              key TEXT PRIMARY KEY,
              value TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            """
        )
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
              task_id TEXT PRIMARY KEY,
              session_id TEXT NOT NULL,
              goal TEXT NOT NULL DEFAULT '',
              status TEXT NOT NULL DEFAULT 'running',
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              final_answer TEXT NOT NULL DEFAULT '',
              next_steps TEXT NOT NULL DEFAULT '',
              summary TEXT NOT NULL DEFAULT '',
              FOREIGN KEY(session_id) REFERENCES sessions(session_id)
            );
            """
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_tasks_session_id_task_id ON tasks(session_id, task_id);"
        )
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tool_events (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              session_id TEXT NOT NULL,
              tool_name TEXT NOT NULL,
              tool_args TEXT NOT NULL DEFAULT '',
              observation TEXT NOT NULL DEFAULT '',
              created_at TEXT NOT NULL,
              FOREIGN KEY(session_id) REFERENCES sessions(session_id)
            );
            """
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_tool_events_session_id_id ON tool_events(session_id, id);"
        )
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS artifacts (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              session_id TEXT NOT NULL,
              kind TEXT NOT NULL DEFAULT 'path',
              action TEXT NOT NULL DEFAULT '',
              value TEXT NOT NULL,
              created_at TEXT NOT NULL,
              FOREIGN KEY(session_id) REFERENCES sessions(session_id)
            );
            """
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_artifacts_session_id_id ON artifacts(session_id, id);"
        )
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS outcomes (
              session_id TEXT PRIMARY KEY,
              final_answer TEXT NOT NULL DEFAULT '',
              next_steps TEXT NOT NULL DEFAULT '',
              updated_at TEXT NOT NULL,
              FOREIGN KEY(session_id) REFERENCES sessions(session_id)
            );
            """
        )
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              session_id TEXT NOT NULL,
              role TEXT NOT NULL,
              content TEXT NOT NULL,
              created_at TEXT NOT NULL,
              FOREIGN KEY(session_id) REFERENCES sessions(session_id)
            );
            """
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_session_id_id ON messages(session_id, id);"
        )
        self._conn.commit()

    def _ensure_session_row(self):
        now = _now_iso()
        self._conn.execute(
            "INSERT OR IGNORE INTO sessions(session_id, created_at, updated_at, summary) VALUES(?,?,?,?)",
            (self.session_id, now, now, ""),
        )
        self._conn.commit()

    def _redact(self, text: str) -> str:
        if not self.redact_secrets:
            return text
        if not text:
            return ""

        s = str(text)
        patterns = [
            # Common env-like secrets
            (r"(?i)(NVIDIA_API_KEY\s*=\s*)([^\s]+)", r"\1[REDACTED]"),
            (r"(?i)(OPENAI_API_KEY\s*=\s*)([^\s]+)", r"\1[REDACTED]"),
            (r"(?i)(API[_-]?KEY\s*=\s*)([^\s]+)", r"\1[REDACTED]"),
            (r"(?i)(TOKEN\s*=\s*)([^\s]+)", r"\1[REDACTED]"),
            # Bearer tokens
            (r"(?i)(Authorization:\s*Bearer\s+)([A-Za-z0-9._-]+)", r"\1[REDACTED]"),
            (r"(?i)(Bearer\s+)([A-Za-z0-9._-]{12,})", r"\1[REDACTED]"),
            # nvapi keys shown in banner
            (r"(?i)(nvapi-[A-Za-z0-9_-]{8,})", "[REDACTED]"),
        ]
        for pat, repl in patterns:
            try:
                s = re.sub(pat, repl, s)
            except Exception:
                continue
        return s

    @property
    def turn_count(self) -> int:
        cur = self._conn.execute(
            "SELECT COUNT(*) FROM messages WHERE session_id=? AND role='user'",
            (self.session_id,),
        )
        return int(cur.fetchone()[0])

    def add(self, role: str, content: str):
        role = (role or "").strip()
        if role not in ("user", "assistant", "system"):
            role = "user"
        content = self._redact(str(content or ""))
        now = _now_iso()
        self._conn.execute(
            "INSERT INTO messages(session_id, role, content, created_at) VALUES(?,?,?,?)",
            (self.session_id, role, content, now),
        )
        self._conn.execute(
            "UPDATE sessions SET updated_at=? WHERE session_id=?",
            (now, self.session_id),
        )
        self._conn.commit()

        # Trim oldest messages if needed.
        if self.max_messages > 0:
            cur = self._conn.execute(
                "SELECT COUNT(*) FROM messages WHERE session_id=?", (self.session_id,)
            )
            count = int(cur.fetchone()[0])
            if count > self.max_messages:
                to_drop = count - self.max_messages

                # OpenClaw-inspired pre-compaction flush: save dropped messages to disk
                try:
                    cur_drop = self._conn.execute(
                        "SELECT role, content FROM messages WHERE session_id=? ORDER BY id ASC LIMIT ?",
                        (self.session_id, to_drop)
                    )
                    dropped_msgs = cur_drop.fetchall()
                    if dropped_msgs:
                        overflow_dir = os.path.join(self.workspace, "memory")
                        os.makedirs(overflow_dir, exist_ok=True)
                        overflow_file = os.path.join(overflow_dir, f"overflow-{self.session_id}.md")
                        with open(overflow_file, "a", encoding="utf-8") as f:
                            for r, c in dropped_msgs:
                                f.write(f"**{r.upper()}**: {c[:500]}...\n\n")
                except Exception:
                    pass

                # Delete oldest rows by id.
                self._conn.execute(
                    """
                    DELETE FROM messages
                    WHERE id IN (
                      SELECT id FROM messages
                      WHERE session_id=?
                      ORDER BY id ASC
                      LIMIT ?
                    )
                    """,
                    (self.session_id, to_drop),
                )
                self._conn.commit()

    def get_messages(self) -> list[dict]:
        cur = self._conn.execute(
            "SELECT role, content, created_at FROM messages WHERE session_id=? ORDER BY id ASC",
            (self.session_id,),
        )
        rows = [_Msg(*r) for r in cur.fetchall()]
        return [{"role": r.role, "content": r.content} for r in rows]

    def import_messages(self, messages: list[dict]):
        """Import legacy messages into this session (best-effort)."""
        if not messages:
            return
        now = _now_iso()
        rows = []
        for msg in messages:
            try:
                role = (msg.get("role") or "user").strip()
                content = self._redact(str(msg.get("content") or ""))
                rows.append((self.session_id, role, content, now))
            except Exception:
                continue
        if not rows:
            return
        self._conn.executemany(
            "INSERT INTO messages(session_id, role, content, created_at) VALUES(?,?,?,?)",
            rows,
        )
        self._conn.execute(
            "UPDATE sessions SET updated_at=? WHERE session_id=?",
            (now, self.session_id),
        )
        self._conn.commit()

    def record_tool_event(
        self, tool_name: str, tool_args: str = "", observation: str = ""
    ):
        now = _now_iso()
        self._conn.execute(
            "INSERT INTO tool_events(session_id, tool_name, tool_args, observation, created_at) VALUES(?,?,?,?,?)",
            (
                self.session_id,
                tool_name or "",
                self._redact(tool_args or ""),
                self._redact(observation or ""),
                now,
            ),
        )
        self._conn.execute(
            "UPDATE sessions SET updated_at=? WHERE session_id=?",
            (now, self.session_id),
        )
        self._conn.commit()

    def record_artifact(self, value: str, action: str = "", kind: str = "path"):
        if not value:
            return
        now = _now_iso()
        self._conn.execute(
            "INSERT INTO artifacts(session_id, kind, action, value, created_at) VALUES(?,?,?,?,?)",
            (self.session_id, kind or "path", action or "", value, now),
        )
        self._conn.execute(
            "UPDATE sessions SET updated_at=? WHERE session_id=?",
            (now, self.session_id),
        )
        self._conn.commit()

    def set_outcome(self, final_answer: str = "", next_steps: str = ""):
        now = _now_iso()
        self._conn.execute(
            "INSERT OR REPLACE INTO outcomes(session_id, final_answer, next_steps, updated_at) VALUES(?,?,?,?)",
            (self.session_id, final_answer or "", next_steps or "", now),
        )
        self._conn.execute(
            "UPDATE sessions SET updated_at=? WHERE session_id=?",
            (now, self.session_id),
        )
        self._conn.commit()

    def start_task(self, task_id: str, goal: str):
        if not task_id:
            return
        now = _now_iso()
        self._conn.execute(
            """
            INSERT OR REPLACE INTO tasks(task_id, session_id, goal, status, created_at, updated_at, final_answer, next_steps, summary)
            VALUES(?,?,?,?,?,?,?,?,?)
            """,
            (
                task_id,
                self.session_id,
                self._redact(goal or ""),
                "running",
                now,
                now,
                "",
                "",
                "",
            ),
        )
        self._conn.commit()

    def update_task(self, task_id: str, status: str | None = None):
        if not task_id:
            return
        now = _now_iso()
        if status:
            self._conn.execute(
                "UPDATE tasks SET status=?, updated_at=? WHERE task_id=?",
                (status, now, task_id),
            )
        else:
            self._conn.execute(
                "UPDATE tasks SET updated_at=? WHERE task_id=?", (now, task_id)
            )
        self._conn.commit()

    def complete_task(
        self,
        task_id: str,
        final_answer: str = "",
        next_steps: str = "",
        summary: str = "",
    ):
        if not task_id:
            return
        now = _now_iso()
        self._conn.execute(
            """
            UPDATE tasks
            SET status=?, updated_at=?, final_answer=?, next_steps=?, summary=?
            WHERE task_id=?
            """,
            (
                "completed",
                now,
                self._redact(final_answer or ""),
                self._redact(next_steps or ""),
                self._redact(summary or ""),
                task_id,
            ),
        )
        self._conn.commit()

    def set_preference(self, key: str, value: str):
        k = (key or "").strip()
        if not k:
            return
        now = _now_iso()
        self._conn.execute(
            "INSERT OR REPLACE INTO preferences(key, value, updated_at) VALUES(?,?,?)",
            (k, self._redact(value or ""), now),
        )
        self._conn.commit()

    def get_preferences(self) -> dict:
        cur = self._conn.execute("SELECT key, value FROM preferences ORDER BY key ASC")
        out = {}
        for k, v in cur.fetchall():
            out[str(k)] = str(v)
        return out

    def set_summary(self, text: str):
        now = _now_iso()
        self._conn.execute(
            "UPDATE sessions SET summary=?, updated_at=? WHERE session_id=?",
            (text or "", now, self.session_id),
        )
        self._conn.commit()

    def summary(self) -> str:
        cur = self._conn.execute(
            "SELECT summary FROM sessions WHERE session_id=?", (self.session_id,)
        )
        row = cur.fetchone()
        return (row[0] if row else "") or ""

    def clear(self):
        self._conn.execute(
            "DELETE FROM messages WHERE session_id=?", (self.session_id,)
        )
        self._conn.execute(
            "UPDATE sessions SET summary='', updated_at=? WHERE session_id=?",
            (_now_iso(), self.session_id),
        )
        self._conn.commit()

    def close(self):
        try:
            self._conn.close()
        except Exception:
            pass
