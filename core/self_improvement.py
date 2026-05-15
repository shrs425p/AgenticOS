"""
Self-Improvement ("Dreaming") module for AgenticOs.

Analyzes past task logs and failures to extract "Lessons Learned" 
and write them to MEMORY.md. Can be triggered via `python main.py --dream`
or called programmatically at the start of a new session.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional


class SelfImprovementDaemon:
    """Analyzes historical task performance and writes learned lessons to MEMORY.md."""

    def __init__(self, workspace_root: str, llm_client: Optional[Any] = None, cfg: Optional[Dict] = None):
        self.workspace = Path(workspace_root).resolve()
        self.cfg = cfg or {}
        self.memory_dir = self.workspace / "memory"
        self.memory_file = self.workspace / "MEMORY.md"
        self.llm_client = llm_client
        self.dream_marker_file = self.memory_dir / ".last_dream"

        # Heuristics
        heuristics = self.cfg.get("heuristics", {})
        self.dream_interval_hours = int(heuristics.get("dream_interval_hours", 6))
        self.slow_task_threshold = int(heuristics.get("slow_task_threshold_seconds", 120))
        self.dream_task_limit = int(heuristics.get("dream_task_limit", 15))

    def should_dream(self, force: bool = False) -> bool:
        """Check if enough time has passed since the last dream cycle."""
        if force:
            return True
        if not self.dream_marker_file.exists():
            return True
        try:
            last_dream = datetime.fromisoformat(
                self.dream_marker_file.read_text(encoding="utf-8").strip()
            )
            # Dream at most once every configured interval
            return datetime.now() - last_dream > timedelta(hours=self.dream_interval_hours)
        except Exception:
            return True

    def dream(self, force: bool = False) -> str:
        """
        The main "Dreaming" loop.
        
        1. Loads the task_tracking.json to find recent failures and slow tasks.
        2. Loads recent daily logs for context.
        3. Asks the LLM to generate "Lessons Learned".
        4. Appends the lessons to MEMORY.md.
        """
        if not self.should_dream(force):
            return "Dream cycle skipped (too recent)."

        tracking_file = self.memory_dir / "task_tracking.json"
        if not tracking_file.exists():
            return "No task history to analyze."

        try:
            with open(tracking_file, "r", encoding="utf-8") as f:
                tracking = json.load(f)
        except Exception as e:
            return f"Error reading task history: {e}"

        tasks = tracking.get("completed_tasks", [])
        if not tasks:
            return "No completed tasks to reflect on."

        # Focus on failures and slow tasks
        failures = [t for t in tasks if not t.get("success", True)]
        slow_tasks = [
            t for t in tasks
            if t.get("duration", 0) > self.slow_task_threshold
        ]
        all_interesting = failures + slow_tasks
        if not all_interesting:
            # Even if everything went well, reflect on patterns
            all_interesting = tasks[-self.dream_task_limit:]

        # Deduplicate
        seen_goals = set()
        unique_tasks = []
        for t in all_interesting:
            g = t.get("goal", "")
            if g not in seen_goals:
                seen_goals.add(g)
                unique_tasks.append(t)

        # Generate reflections
        lessons = self._generate_reflections(unique_tasks)
        if not lessons:
            return "Dream cycle completed but no new lessons generated."

        # Write to MEMORY.md
        self._append_lessons(lessons)

        # Mark the dream as done
        self.memory_dir.mkdir(exist_ok=True)
        self.dream_marker_file.write_text(
            datetime.now().isoformat(), encoding="utf-8"
        )

        return f"Dream cycle completed. {len(lessons)} lessons written to MEMORY.md."

    def _generate_reflections(self, tasks: List[Dict]) -> List[str]:
        """Use LLM to reflect on past task performance."""
        task_report_lines = []
        for i, t in enumerate(tasks[:self.dream_task_limit], 1):
            status = "FAILED" if not t.get("success", True) else "SUCCESS"
            goal = t.get("goal", "Unknown")[:200]
            dur = t.get("duration", 0)
            tools = ", ".join(t.get("tools_used", [])[:5])
            result_snippet = t.get("result", "")[:200]
            task_report_lines.append(
                f"Task {i} [{status}] (Duration: {dur:.0f}s)\n"
                f"  Goal: {goal}\n"
                f"  Tools: {tools}\n"
                f"  Result: {result_snippet}\n"
            )

        task_report = "\n".join(task_report_lines)

        if self.llm_client and hasattr(self.llm_client, "chat"):
            try:
                reflection_cfg = self.cfg.get("prompts", {}).get("reflection", {})
                system = reflection_cfg.get("system", "").strip()
                if not system:
                    system = (
                        "You are the Self-Improvement unit of an AI agent called AgenticOS. "
                        "You are performing a 'Dream Cycle' -- reviewing past task performance "
                        "to extract actionable lessons. You MUST output exactly 3 to 5 bullet points. "
                        "Each bullet should be a concrete, specific lesson (not generic advice). "
                        "Focus on:\n"
                        "- Mistakes that should be avoided next time\n"
                        "- Successful patterns worth repeating\n"
                        "- Environment-specific facts discovered (file paths, configs, user preferences)\n\n"
                        "Format: one bullet point per line, starting with '- '."
                    )
                response = self.llm_client.chat(
                    messages=[{"role": "user", "content": f"Recent task history:\n\n{task_report}"}],
                    system=system,
                )
                if response:
                    lines = [
                        line.strip().lstrip("-").lstrip("*").strip()
                        for line in response.split("\n")
                        if line.strip() and len(line.strip()) > 10
                    ]
                    return lines[:5]
            except Exception as e:
                print(f"Warning: LLM reflection failed: {e}")

        # Fallback: simple heuristic-based reflections
        lessons = []
        reflection_prompts = self.cfg.get("prompts", {}).get("dream_cycle", {}).get("fallback_lessons", {})
        
        failures = [t for t in tasks if not t.get("success", True)]
        if failures:
            goals = [t.get("goal", "")[:80] for t in failures[:3]]
            tmpl = reflection_prompts.get("failures", "Recent failures ({count} tasks) include: {goals}")
            lessons.append(tmpl.format(count=len(failures), goals="; ".join(goals)))

        slow = [t for t in tasks if t.get("duration", 0) > self.slow_task_threshold]
        if slow:
            avg_dur = sum(t.get("duration", 0) for t in slow) / len(slow)
            tmpl = reflection_prompts.get("slow_tasks", "Some tasks are slow (avg {avg_dur:.0f}s). Consider breaking complex tasks into sub-steps.")
            lessons.append(tmpl.format(avg_dur=avg_dur))

        # Tool frequency
        tool_freq: Dict[str, int] = {}
        for t in tasks:
            for tool in t.get("tools_used", []):
                tool_freq[tool] = tool_freq.get(tool, 0) + 1
        if tool_freq:
            top = sorted(tool_freq.items(), key=lambda x: x[1], reverse=True)[:3]
            tmpl = reflection_prompts.get("tool_usage", "Most relied-on tools: {tools}")
            tools_str = ", ".join(f"{name} ({count}x)" for name, count in top)
            lessons.append(tmpl.format(tools=tools_str))

        return lessons

    def _append_lessons(self, lessons: List[str]):
        """Append lessons to MEMORY.md."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        reflection_cfg = self.cfg.get("prompts", {}).get("reflection", {})
        header_tmpl = reflection_cfg.get("memory_block_header", "").strip()
        if not header_tmpl:
            header_tmpl = "## Dream Cycle - {timestamp}\n\n**Self-Reflection (Automatically Generated):**"
        
        block = "\n" + header_tmpl.format(timestamp=timestamp) + "\n\n"
        for lesson in lessons:
            block += f"- {lesson}\n"
        block += "\n---\n"

        try:
            with open(self.memory_file, "a", encoding="utf-8") as f:
                f.write(block)
        except Exception as e:
            print(f"Warning: Failed to write dream lessons: {e}")


def run_dream_cycle(workspace_root: str, llm_client=None, force: bool = False, cfg: Optional[Dict] = None) -> str:
    """Convenience function to run a dream cycle."""
    daemon = SelfImprovementDaemon(workspace_root, llm_client, cfg)
    return daemon.dream(force=force)
