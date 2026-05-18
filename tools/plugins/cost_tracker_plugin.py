"""Cost & token budget tracker plugin for AgenticOs.

Exposes a ``get_usage_report`` tool so the agent can query its own API
consumption and estimated USD costs.
"""

import os

from core.tool_registry import tool

_TRACKER = None


def _get_tracker():
    global _TRACKER
    if _TRACKER is not None:
        return _TRACKER
    try:
        from core.cost_tracker import CostTracker

        data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data")
        _TRACKER = CostTracker(data_dir=data_dir)
    except Exception:
        pass
    return _TRACKER


@tool(
    name="get_usage_report",
    desc="Return API token usage and estimated cost. Args: period ('session', 'today', 'all'). Defaults to 'session'.",
    category="system",
    version="1.0.0",
)
def get_usage_report(period: str = "session") -> str:
    """Generate a token usage and cost report.

    Args:
        period: One of 'session' (current session), 'today', or 'all' (lifetime).

    Returns:
        Formatted usage report with provider breakdown.
    """
    tracker = _get_tracker()
    if tracker is None:
        return "Cost tracker not available."

    allowed = ("session", "today", "all")
    if period not in allowed:
        period = "session"

    try:
        report = tracker.get_report(period=period)
    except Exception as exc:
        return f"Error generating report: {exc}"

    lines = [
        f"# Usage Report — period: {report['period']}",
        f"Session ID  : {report['session_id']}",
        f"Session cost: ${report['session_cost_usd']:.6f}",
        f"Total cost  : ${report['total_cost_usd']:.6f}  ({report['total_calls']} calls)",
    ]
    if report.get("budget_usd"):
        lines.append(f"Budget      : ${report['budget_usd']:.4f}  ({'OVER BUDGET' if report['over_budget'] else 'OK'})")

    by_prov = report.get("by_provider", {})
    if by_prov:
        lines.append("\nBy provider:")
        for prov, stats in by_prov.items():
            lines.append(
                f"  {prov:<14} calls={stats['calls']:<5} "
                f"prompt={stats['prompt_tokens']:<8} "
                f"completion={stats['completion_tokens']:<8} "
                f"cost=${stats['cost_usd']:.6f}"
            )

    return "\n".join(lines)
