"""Task scheduler plugin for AgenticOs.

Exposes two tools:
- ``schedule_task`` — schedule a recurring task by cron or interval
- ``list_scheduled_tasks`` — show all active scheduled tasks
- ``remove_scheduled_task`` — remove a scheduled task by ID
"""

from core.tool_registry import tool

_SCHEDULER = None


def _get_scheduler():
    """Lazily fetch the scheduler from the ToolRegistry registry globals."""
    global _SCHEDULER
    if _SCHEDULER is not None:
        return _SCHEDULER
    # Try to get the singleton from the registry
    try:
        from core import task_scheduler as _ts_mod  # noqa: F401

        if hasattr(_ts_mod, "_GLOBAL_SCHEDULER"):
            _SCHEDULER = _ts_mod._GLOBAL_SCHEDULER
    except Exception:
        pass
    return _SCHEDULER


@tool(
    name="schedule_task",
    desc="Schedule a recurring task. Args: expr (cron '0 9 * * *' or 'every 6 hours'), description (task string).",
    category="scheduler",
    version="1.0.0",
)
def schedule_task(expr: str, description: str) -> str:
    """Schedule a recurring task.

    Args:
        expr: Cron expression ('0 9 * * *') or relative interval ('every 6 hours').
        description: The task description to run on schedule.

    Returns:
        Confirmation message with the assigned task ID.
    """
    from core.task_scheduler import TaskScheduler

    sched = _get_scheduler()
    if sched is None:
        # Create a temporary scheduler backed by the default workspace
        import os

        workspace = os.environ.get("AGENTICOS_WORKSPACE", "workspace")
        sched = TaskScheduler(workspace=workspace)

    try:
        entry = sched.add_task(expr=expr, description=description)
        return (
            f"Task scheduled successfully.\n"
            f"  ID:    {entry['id']}\n"
            f"  Expr:  {expr}\n"
            f"  Task:  {description}\n"
        )
    except ValueError as exc:
        return f"Error: {exc}"


@tool(
    name="list_scheduled_tasks",
    desc="List all currently scheduled recurring tasks.",
    category="scheduler",
    version="1.0.0",
)
def list_scheduled_tasks() -> str:
    """Return a formatted list of all scheduled tasks.

    Returns:
        Human-readable table of task ID, expression, description, and run count.
    """
    sched = _get_scheduler()
    if sched is None:
        return "No scheduler is active. Start the agent first."

    tasks = sched.list_tasks()
    if not tasks:
        return "No scheduled tasks."

    lines = [f"{'ID':<20} {'Expr':<20} {'Runs':<6} Description"]
    lines.append("-" * 80)
    for t in tasks:
        lines.append(
            f"{t['id']:<20} {t['expr']:<20} {t.get('run_count', 0):<6} {t['description']}"
        )
    return "\n".join(lines)


@tool(
    name="remove_scheduled_task",
    desc="Remove a scheduled task by its ID. Args: task_id (string).",
    category="scheduler",
    version="1.0.0",
)
def remove_scheduled_task(task_id: str) -> str:
    """Remove a scheduled task by ID.

    Args:
        task_id: The unique ID returned by schedule_task.

    Returns:
        Success or error message.
    """
    sched = _get_scheduler()
    if sched is None:
        return "No scheduler is active."

    removed = sched.remove_task(task_id)
    if removed:
        return f"Task '{task_id}' removed successfully."
    return f"Task '{task_id}' not found."
