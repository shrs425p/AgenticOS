"""Persistent task scheduler (cron mode) for AgenticOs.

Supports:
- Cron-style expressions: "0 9 * * *"
- Relative intervals: "every 6 hours", "every 30 minutes", "every 1 day"

Schedules are persisted to ``workspace/memory/schedule.json`` so they survive
restarts.  The background thread fires the agent's ``run()`` callback when a
scheduled task is due.
"""

from __future__ import annotations

import json
import logging
import re
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Interval parsing helpers
# ---------------------------------------------------------------------------

_INTERVAL_RE = re.compile(
    r"every\s+(\d+(?:\.\d+)?)\s*(second|minute|hour|day|week)s?",
    re.IGNORECASE,
)

_UNIT_TO_SECONDS: Dict[str, float] = {
    "second": 1,
    "minute": 60,
    "hour": 3600,
    "day": 86400,
    "week": 604800,
}


def _parse_interval(expr: str) -> Optional[float]:
    """Parse a relative interval expression and return seconds, or None."""
    m = _INTERVAL_RE.search(expr)
    if not m:
        return None
    amount = float(m.group(1))
    unit = m.group(2).lower()
    return amount * _UNIT_TO_SECONDS.get(unit, 0)


def _parse_cron(expr: str) -> Optional[Dict[str, int]]:
    """Parse a 5-field cron expression into a dict with keys minute/hour/dom/month/dow.

    Returns None if the expression cannot be parsed.  Wildcards (*) are stored
    as ``-1``.
    """
    parts = expr.strip().split()
    if len(parts) != 5:
        return None
    fields = ("minute", "hour", "dom", "month", "dow")
    result: Dict[str, int] = {}
    try:
        for name, part in zip(fields, parts):
            result[name] = -1 if part == "*" else int(part)
    except ValueError:
        return None
    return result


def _cron_matches(cron: Dict[str, int], dt: datetime) -> bool:
    """Return True if *dt* matches the cron spec."""
    mapping = {
        "minute": dt.minute,
        "hour": dt.hour,
        "dom": dt.day,
        "month": dt.month,
        "dow": dt.isoweekday() % 7,  # 0=Sun … 6=Sat (standard cron)
    }
    return all(v == -1 or mapping[k] == v for k, v in cron.items())


# ---------------------------------------------------------------------------
# TaskScheduler
# ---------------------------------------------------------------------------


class TaskScheduler:
    """Background scheduler that fires tasks at configured intervals.

    Args:
        workspace: Path to the agent workspace directory.
        run_callback: Callable that accepts a task description string and
                      executes it (typically ``agent.run``).
        poll_interval: How often (seconds) to poll for due tasks (default 60).
    """

    _SCHEDULE_FILE = "schedule.json"

    def __init__(
        self,
        workspace: str,
        run_callback: Optional[Callable[[str], Any]] = None,
        poll_interval: float = 60.0,
    ):
        self.workspace = Path(workspace).resolve()
        self.memory_dir = self.workspace / "memory"
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.schedule_file = self.memory_dir / self._SCHEDULE_FILE
        self.run_callback = run_callback
        self.poll_interval = max(1.0, poll_interval)

        self._lock = threading.RLock()
        self._schedules: List[Dict[str, Any]] = self._load()
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> List[Dict[str, Any]]:
        if not self.schedule_file.exists():
            return []
        try:
            with open(self.schedule_file, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            return data if isinstance(data, list) else []
        except Exception as exc:
            logger.warning("TaskScheduler: failed to load schedule: %s", exc)
            return []

    def _save(self):
        try:
            with self._lock:
                with open(self.schedule_file, "w", encoding="utf-8") as fh:
                    json.dump(self._schedules, fh, indent=2)
        except Exception as exc:
            logger.error("TaskScheduler: failed to save schedule: %s", exc)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_task(self, expr: str, description: str) -> Dict[str, Any]:
        """Add a scheduled task.

        Args:
            expr: A cron expression ("0 9 * * *") or relative interval
                  ("every 6 hours").
            description: The task to run when the trigger fires.

        Returns:
            The new schedule entry dict.
        """
        entry: Dict[str, Any] = {
            "id": f"sched_{int(time.time() * 1000)}",
            "expr": expr,
            "description": description,
            "created_at": datetime.now().isoformat(),
            "last_run": None,
            "run_count": 0,
        }
        # Validate expression
        interval_secs = _parse_interval(expr)
        cron = _parse_cron(expr) if interval_secs is None else None
        if interval_secs is None and cron is None:
            raise ValueError(
                f"Cannot parse schedule expression: '{expr}'. "
                "Use a 5-field cron string or 'every N hours/minutes/days'."
            )
        if interval_secs is not None:
            entry["interval_seconds"] = interval_secs
            entry["next_run"] = (time.time() + interval_secs)
        else:
            entry["cron"] = cron
            entry["next_run"] = None  # evaluated at poll time

        with self._lock:
            self._schedules.append(entry)
        self._save()
        logger.info("TaskScheduler: added '%s' with expr '%s'", entry["id"], expr)
        return entry

    def remove_task(self, task_id: str) -> bool:
        """Remove a scheduled task by ID.  Returns True if found and removed."""
        with self._lock:
            before = len(self._schedules)
            self._schedules = [s for s in self._schedules if s.get("id") != task_id]
            removed = len(self._schedules) < before
        if removed:
            self._save()
        return removed

    def list_tasks(self) -> List[Dict[str, Any]]:
        """Return a copy of all scheduled tasks."""
        with self._lock:
            return list(self._schedules)

    # ------------------------------------------------------------------
    # Background thread
    # ------------------------------------------------------------------

    def start(self):
        """Start the background polling thread."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._poll_loop, daemon=True, name="TaskScheduler"
        )
        self._thread.start()
        logger.info("TaskScheduler: started (poll_interval=%.0fs)", self.poll_interval)

    def stop(self):
        """Stop the background polling thread."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5.0)

    def _poll_loop(self):
        while not self._stop_event.is_set():
            try:
                self._tick()
            except Exception as exc:
                logger.error("TaskScheduler: poll error: %s", exc)
            self._stop_event.wait(timeout=self.poll_interval)

    def _tick(self):
        """Check all schedules and fire any that are due."""
        now = time.time()
        now_dt = datetime.now()
        with self._lock:
            schedules = list(self._schedules)

        for entry in schedules:
            due = False
            if "interval_seconds" in entry:
                next_run = entry.get("next_run") or 0
                if now >= next_run:
                    due = True
            elif "cron" in entry:
                # Fire once per minute-slot; skip if already ran this minute
                last_run = entry.get("last_run")
                if last_run:
                    last_dt = datetime.fromisoformat(last_run)
                    same_minute = (
                        last_dt.year == now_dt.year
                        and last_dt.month == now_dt.month
                        and last_dt.day == now_dt.day
                        and last_dt.hour == now_dt.hour
                        and last_dt.minute == now_dt.minute
                    )
                    if same_minute:
                        continue
                if _cron_matches(entry["cron"], now_dt):
                    due = True

            if due:
                self._fire(entry, now)

    def _fire(self, entry: Dict[str, Any], now: float):
        task_id = entry.get("id", "?")
        description = entry.get("description", "")
        logger.info("TaskScheduler: firing task '%s': %s", task_id, description)

        # Update bookkeeping
        with self._lock:
            for s in self._schedules:
                if s.get("id") == task_id:
                    s["last_run"] = datetime.now().isoformat()
                    s["run_count"] = s.get("run_count", 0) + 1
                    if "interval_seconds" in s:
                        s["next_run"] = now + s["interval_seconds"]
                    break
        self._save()

        if self.run_callback:
            try:
                self.run_callback(description)
            except Exception as exc:
                logger.error(
                    "TaskScheduler: task '%s' raised an error: %s", task_id, exc
                )
