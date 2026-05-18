"""Agent Planning Phase with Rollback for AgenticOs.

Adds an optional structured pre-planning step before the main execution loop.
The agent generates a numbered JSON plan, optionally requests user approval,
then executes each step while recording reversible undo operations so that
partial failures can be rolled back.

Plan format (stored in ``workspace/memory/active_plan.json``)::

    [
      {
        "step": 1,
        "description": "Fetch the Python trending repos",
        "tool": "web_search",
        "args": {"query": "trending python github"},
        "reversible": false,
        "undo": null,
        "status": "pending"   # pending | running | done | failed | skipped
      },
      ...
    ]
"""

from __future__ import annotations

import json
import logging
import os
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

_PLAN_FILE = "active_plan.json"


class AgentPlanner:
    """Manages the plan lifecycle: creation, persistence, execution, rollback.

    Args:
        workspace: Path to the agent workspace.
        dispatch_fn: Callable ``(tool_name, args) -> result`` for executing steps.
        confirm_fn: Optional callable ``(prompt) -> bool`` for user approval.
    """

    def __init__(
        self,
        workspace: str,
        dispatch_fn: Optional[Callable[[str, Any], Any]] = None,
        confirm_fn: Optional[Callable[[str], bool]] = None,
    ):
        self.workspace = Path(workspace).resolve()
        self.memory_dir = self.workspace / "memory"
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.plan_file = self.memory_dir / _PLAN_FILE
        self.dispatch_fn = dispatch_fn
        self.confirm_fn = confirm_fn
        self._plan: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def load(self) -> List[Dict[str, Any]]:
        """Load the active plan from disk (returns [] if none exists)."""
        if not self.plan_file.exists():
            return []
        try:
            with open(self.plan_file, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            self._plan = data if isinstance(data, list) else []
        except Exception as exc:
            logger.warning("AgentPlanner: failed to load plan: %s", exc)
            self._plan = []
        return self._plan

    def save(self):
        """Persist the current plan to disk."""
        try:
            with open(self.plan_file, "w", encoding="utf-8") as fh:
                json.dump(self._plan, fh, indent=2)
        except Exception as exc:
            logger.error("AgentPlanner: failed to save plan: %s", exc)

    def clear(self):
        """Remove the active plan from disk and memory."""
        self._plan = []
        if self.plan_file.exists():
            try:
                os.remove(self.plan_file)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Plan construction
    # ------------------------------------------------------------------

    def set_plan(self, steps: List[Dict[str, Any]]):
        """Set the current plan from a list of step dicts.

        Each step should contain at minimum ``step``, ``description``, ``tool``,
        and ``args``.  Missing fields are filled with sensible defaults.
        """
        normalised = []
        for i, raw in enumerate(steps, 1):
            step: Dict[str, Any] = {
                "step": raw.get("step", i),
                "description": raw.get("description", f"Step {i}"),
                "tool": raw.get("tool", ""),
                "args": raw.get("args", {}),
                "reversible": bool(raw.get("reversible", False)),
                "undo": raw.get("undo"),
                "status": raw.get("status", "pending"),
                "result": raw.get("result"),
                "error": raw.get("error"),
            }
            normalised.append(step)
        self._plan = normalised
        self.save()

    @staticmethod
    def parse_plan_from_text(text: str) -> List[Dict[str, Any]]:
        """Try to extract a JSON plan array from raw LLM output.

        Looks for the first ``[...]`` JSON array in the text.
        Returns an empty list if nothing parseable is found.
        """
        # Find first '[' and its matching ']'
        start = text.find("[")
        if start == -1:
            return []
        depth = 0
        in_str = False
        escape = False
        for i in range(start, len(text)):
            ch = text[i]
            if escape:
                escape = False
                continue
            if ch == "\\" and in_str:
                escape = True
                continue
            if ch == '"' and not escape:
                in_str = not in_str
                continue
            if in_str:
                continue
            if ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start : i + 1])
                    except Exception:
                        return []
        return []

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def pending_steps(self) -> List[Dict[str, Any]]:
        """Return steps that have not been completed."""
        return [s for s in self._plan if s.get("status") in ("pending", "running")]

    def execute_step(self, step: Dict[str, Any]) -> str:
        """Execute a single plan step and update its status.

        Returns:
            Result string from the tool, or an error message.
        """
        tool_name = step.get("tool", "")
        args = step.get("args", {})
        step["status"] = "running"
        self.save()

        try:
            if self.dispatch_fn and tool_name:
                result = self.dispatch_fn(tool_name, args)
            else:
                result = f"(no dispatch_fn; skipped step {step['step']})"
            step["status"] = "done"
            step["result"] = str(result)[:2000]
            self.save()
            return str(result)
        except Exception as exc:
            step["status"] = "failed"
            step["error"] = str(exc)
            self.save()
            logger.error("AgentPlanner: step %d failed: %s", step["step"], exc)
            return f"ERROR: {exc}"

    # ------------------------------------------------------------------
    # Rollback
    # ------------------------------------------------------------------

    def rollback(self) -> List[str]:
        """Attempt to undo completed reversible steps in reverse order.

        Returns:
            List of messages describing what was (or wasn't) undone.
        """
        messages = []
        completed = [
            s for s in reversed(self._plan)
            if s.get("status") == "done" and s.get("reversible") and s.get("undo")
        ]

        for step in completed:
            undo_info = step["undo"]
            msg = self._perform_undo(step, undo_info)
            messages.append(msg)
            step["status"] = "skipped"
        self.save()
        return messages

    def _perform_undo(self, step: Dict[str, Any], undo_info: Any) -> str:
        """Execute an undo operation described by *undo_info*.

        ``undo_info`` can be:
        - A dict with ``{"tool": ..., "args": ...}`` — call that tool.
        - A string — just return it as a descriptive message.
        """
        if isinstance(undo_info, dict) and "tool" in undo_info:
            undo_tool = undo_info["tool"]
            undo_args = undo_info.get("args", {})
            try:
                if self.dispatch_fn:
                    result = self.dispatch_fn(undo_tool, undo_args)
                    return f"Rolled back step {step['step']} via {undo_tool}: {str(result)[:200]}"
                return f"No dispatch_fn; cannot undo step {step['step']}"
            except Exception as exc:
                return f"Rollback of step {step['step']} failed: {exc}"
        elif isinstance(undo_info, str):
            return f"Step {step['step']} undo note: {undo_info}"
        return f"Step {step['step']}: no undo action defined."

    # ------------------------------------------------------------------
    # Human-readable summary
    # ------------------------------------------------------------------

    def plan_summary(self) -> str:
        """Return a formatted string summary of the plan."""
        if not self._plan:
            return "(no active plan)"
        lines = ["## Active Plan\n"]
        status_icons = {
            "pending": "○",
            "running": "►",
            "done": "✓",
            "failed": "✗",
            "skipped": "—",
        }
        for step in self._plan:
            icon = status_icons.get(step.get("status", "pending"), "?")
            lines.append(
                f"{icon} Step {step['step']}: {step['description']} "
                f"[{step.get('tool', 'no-tool')}]"
            )
        return "\n".join(lines)
