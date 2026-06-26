"""Task tracking helpers for autonomous runs."""

import json
import os
import re
from datetime import datetime


class TaskTracker:
    def __init__(self, workspace: str, session_id: str | None = None, cfg: dict | None = None):
        self.workspace = workspace
        self.cfg = cfg or {}
        self.tasks_dir = os.path.join(workspace, "tasks")
        self.session_id = session_id or "default"
        # Use session_id for active task files (one per session, not per task)
        self.active_json = os.path.join(
            self.tasks_dir, f"active_task_{self.session_id}.json"
        )
        self.active_md = os.path.join(
            self.tasks_dir, f"active_task_{self.session_id}.md"
        )
        self.current: dict | None = None
        self.tasks: list[dict] = []  # All tasks in this session
        self.load_active_session()

    def load_active_session(self):
        """Load tasks from the active session JSON file on disk."""
        if os.path.exists(self.active_json):
            try:
                with open(self.active_json, "r", encoding="utf-8") as handle:
                    self.tasks = json.load(handle)
                    if self.tasks and isinstance(self.tasks, list):
                        # Look for the last task that is still 'running'
                        for task in reversed(self.tasks):
                            if task.get("status") == "running":
                                self.current = task
                                break
                        # Fallback to the last task if none are 'running'
                        if not self.current and self.tasks:
                            self.current = self.tasks[-1]
            except Exception:
                self.tasks = []
                self.current = None

    def start(self, goal: str, provider: str, model: str):
        """start function."""
        task_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current = {
            "task_id": task_id,
            "goal": goal.strip(),
            "provider": provider,
            "model": model,
            "status": "running",
            "iteration": 0,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "objective": goal.strip(),
            "task": "",
            "plan": [
                "Inspect context and constraints",
                "Choose ops and execute steps",
                "Validate results (lint/spec/smoke)",
                "Summarize changes and next actions",
            ],
            "current_step": "Inspect context and constraints",
            "last_response": "",
            "last_action": "",
            "last_observation": "",
            "final_answer": "",
            "stall_count": 0,
            "plan_version": 1,
            "actions_taken": [],
        }
        self.tasks.append(self.current)
        self._persist()

    def update_from_response(self, response: str, iteration: int):
        """update_from_response function."""
        if not self.current:
            return
        self.current["iteration"] = iteration
        self.current["last_response"] = response.strip()
        extracted = self._extract_sections(response)
        for key, value in extracted.items():
            if key == "plan":
                if value:
                    self.current["plan"] = value
                    self.current["plan_version"] = (
                        int(self.current.get("plan_version", 1)) + 1
                    )
                continue
            if value:
                self.current[key] = value
        self.current["updated_at"] = datetime.now().isoformat()
        self._persist()

    def record_action(self, tool_name: str, args: list[str] | dict | None):
        """record_action function."""
        if not self.current:
            return
        if "actions_taken" not in self.current:
            self.current["actions_taken"] = []
        self.current["actions_taken"].append({
            "tool": tool_name,
            "args": args,
            "timestamp": datetime.now().isoformat()
        })
        
        arg_text = ""
        if isinstance(args, list):
            arg_text = " | ".join(str(arg) for arg in args)
        elif isinstance(args, dict):
            arg_text = ", ".join(f"{k}={v}" for k, v in args.items())
        elif args is not None:
            arg_text = str(args)

        self.current["last_action"] = (
            f"{tool_name} | {arg_text}" if arg_text else tool_name
        )
        self.current["updated_at"] = datetime.now().isoformat()
        self._persist()

    def record_observation(self, observation: str):
        """record_observation function."""
        if not self.current:
            return
        self.current["last_observation"] = observation.strip()
        self.current["updated_at"] = datetime.now().isoformat()
        self._persist()

    def note_stall(self, message: str):
        """note_stall function."""
        if not self.current:
            return
        self.current["stall_count"] = int(self.current.get("stall_count", 0)) + 1
        self.current["last_observation"] = message.strip()
        self.current["updated_at"] = datetime.now().isoformat()
        self._persist()

    def planner_hint(self) -> str:
        """planner_hint function."""
        if not self.current:
            return ""
        return self.cfg.get("prompts", {}).get("planner_hints", {}).get("standard", (
            "Planner reminder: keep OBJECTIVE, PLAN (3-6 steps), and CURRENT_STEP updated based on the latest OBSERVATION. "
            "If you are blocked or looping, revise the PLAN and pick a different approach/tool."
        ))

    def complete(self, final_answer: str):
        """complete function."""
        if not self.current:
            return
        self.current["status"] = "completed"
        self.current["final_answer"] = final_answer.strip()
        self.current["updated_at"] = datetime.now().isoformat()
        self._persist()

    def fail(self, message: str):
        """fail function."""
        if not self.current:
            return
        self.current["status"] = "failed"
        self.current["last_observation"] = message.strip()
        self.current["updated_at"] = datetime.now().isoformat()
        self._persist()

    def _extract_sections(self, response: str) -> dict:
        lines = [line.rstrip() for line in response.splitlines()]
        extracted = {"objective": "", "task": "", "plan": [], "current_step": ""}
        current_block = None

        for raw_line in lines:
            line = raw_line.strip()
            upper = line.upper()
            if upper.startswith("OBJECTIVE:"):
                extracted["objective"] = line.split(":", 1)[1].strip()
                current_block = None
            elif upper.startswith("TASK:"):
                extracted["task"] = line.split(":", 1)[1].strip()
                current_block = None
            elif upper.startswith("CURRENT_STEP:"):
                extracted["current_step"] = line.split(":", 1)[1].strip()
                current_block = None
            elif upper.startswith("PLAN:"):
                current_block = "plan"
            elif current_block == "plan":
                if re.match(r"^(\d+\.|-|\*)\s+", line):
                    extracted["plan"].append(re.sub(r"^(\d+\.|-|\*)\s+", "", line))
                elif line:
                    extracted["plan"].append(line)
                else:
                    current_block = None

        return extracted

    def _persist(self):
        if not self.current:
            return

        # Ensure tasks directory exists
        os.makedirs(self.tasks_dir, exist_ok=True)
        
        # Write all tasks in the session to active files
        with open(self.active_json, "w", encoding="utf-8") as handle:
            json.dump(self.tasks, handle, indent=2)
        with open(self.active_md, "w", encoding="utf-8") as handle:
            handle.write(self._session_markdown())

    def _status_badge(self, status: str) -> str:
        badges = {
            "running": "[RUNNING]",
            "completed": "[COMPLETED]",
            "failed": "[FAILED]",
        }
        return badges.get(status.lower(), f"[{status.upper()}]")

    def _task_markdown(
        self, c: dict, task_num: int = 1, is_current: bool = False
    ) -> str:
        """Render a single task as markdown."""
        prompts = self.cfg.get("prompts", {}).get("task_tracking", {})
        status = self._status_badge(c.get("status", "unknown"))
        current_marker = " **<-- CURRENT**" if is_current else ""

        # Build plan with progress indicators
        plan = c.get("plan", [])
        current_step = c.get("current_step", "")
        if plan:
            plan_lines = []
            for i, step in enumerate(plan, 1):
                marker = (
                    "[x]"
                    if step == current_step or (current_step and current_step in step)
                    else "[ ]"
                )
                plan_lines.append(f"{marker} **{i}.** {step}")
            plan_text = "\n".join(plan_lines)
        else:
            plan_text = "_No plan defined._"

        # Format timestamps
        created = c.get("created_at", "")
        updated = c.get("updated_at", "")

        task_hdr_tmpl = prompts.get("task_header", "### Task {num}: {goal}{marker}")
        
        sections = [
            task_hdr_tmpl.format(num=task_num, goal=c.get('goal', 'Untitled').strip(), marker=current_marker),
            "",
            prompts.get("metadata_header", "#### Metadata"),
            "",
            "| Field | Value |",
            "|-------|-------|",
            f"| **Status** | {status} |",
            f"| **Task ID** | `{c.get('task_id', 'N/A')}` |",
            f"| **Provider** | {c.get('provider', 'N/A')} |",
            f"| **Model** | `{c.get('model', 'N/A')}` |",
            f"| **Iteration** | {c.get('iteration', 0)} |",
            f"| **Stall Count** | {c.get('stall_count', 0)} |",
            f"| **Plan Version** | {c.get('plan_version', 1)} |",
            f"| **Created** | {created} |",
            f"| **Updated** | {updated} |",
            "",
            prompts.get("objective_header", "#### Objective"),
            "",
            c.get("objective", "_Not yet defined._").strip() or "_Not yet defined._",
            "",
            prompts.get("plan_header", "#### Plan & Progress"),
            "",
            plan_text,
            "",
            prompts.get("current_step_header", "#### Current Step"),
            "",
            c.get("current_step", "_Not yet started._").strip() or "_Not yet started._",
            "",
            prompts.get("last_action_header", "#### Last Action"),
            "",
            f"```\n{c.get('last_action', 'None yet.').strip() or 'None yet.'}\n```",
            "",
            prompts.get("last_observation_header", "#### Last Observation"),
            "",
            f"```\n{c.get('last_observation', 'None yet.').strip() or 'None yet.'}\n```",
            "",
        ]

        # Only show final answer section if completed or failed
        if c.get("final_answer"):
            sections.extend(
                [
                    prompts.get("final_answer_header", "#### Final Answer"),
                    "",
                    c.get("final_answer", "").strip(),
                    "",
                ]
            )
        elif c.get("status", "").lower() == "running":
            sections.extend(
                [
                    prompts.get("pending_answer_header", "#### Final Answer (Pending)"),
                    "",
                    "_Task is still in progress..._",
                    "",
                ]
            )

        return "\n".join(sections)

    def _session_markdown(self) -> str:
        """Render the full session with all tasks."""
        prompts = self.cfg.get("prompts", {}).get("task_tracking", {})
        now = datetime.now().isoformat()
        total = len(self.tasks)
        completed = sum(1 for t in self.tasks if t.get("status") == "completed")
        failed = sum(1 for t in self.tasks if t.get("status") == "failed")
        running = sum(1 for t in self.tasks if t.get("status") == "running")

        lines = [
            prompts.get("session_report_title", "# Session Task Report"),
            "",
            prompts.get("session_metadata_header", "## Session Metadata"),
            "",
            "| Field | Value |",
            "|-------|-------|",
            f"| **Session ID** | `{self.session_id}` |",
            f"| **Generated** | {now} |",
            f"| **Total Tasks** | {total} |",
            f"| **Running** | {running} |",
            f"| **Completed** | {completed} |",
            f"| **Failed** | {failed} |",
            "",
            "---",
            "",
        ]

        for i, task in enumerate(self.tasks, 1):
            is_current = task is self.current
            lines.append(self._task_markdown(task, task_num=i, is_current=is_current))
            if i < total:
                lines.extend(["", "---", ""])

        footer_tmpl = prompts.get("footer", "*Generated by AgenticOs | Session `{session_id}`*")
        lines.extend(
            [
                "",
                "---",
                footer_tmpl.format(session_id=self.session_id),
            ]
        )

        return "\n".join(lines)
