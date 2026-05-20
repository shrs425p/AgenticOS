"""Module for log_analyzer.py"""
from __future__ import annotations

import os
from core.tool_registry import tool

def _get_log_path() -> str:
    """Helper to resolve the standard agenticos.log location."""
    # Climbing from tools/plugins/ to project root
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base_dir, "data", "logs", "agenticos.log")

@tool(
    name="search_logs",
    desc="Search for matching query patterns in AgenticOS log files. Args: query (str), limit (int, optional).",
    category="Diagnostics"
)
def search_logs(query: str, limit: int = 50) -> str:
    """Searches case-insensitively for the given string within the logs and outputs matching entries."""
    log_path = _get_log_path()
    if not os.path.exists(log_path):
        return f"Log file not found at: {log_path}"

    try:
        lim = int(limit)
    except Exception:
        lim = 50

    q = (query or "").lower()
    if not q:
        return "Error: query parameter is empty."

    matches = []
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                if q in line.lower():
                    matches.append(line.strip())
                    if len(matches) >= lim:
                        break
        if not matches:
            return f"No matches found for '{query}'."
        return "\n".join(matches)
    except Exception as e:
        return f"Error reading logs: {e}"

@tool(
    name="get_log_errors",
    desc="Scan AgenticOS logs for errors, warnings, and python tracebacks.",
    category="Diagnostics"
)
def get_log_errors() -> str:
    """Extracts summary and occurrences of errors, warnings, and exceptions/tracebacks from logs."""
    log_path = _get_log_path()
    if not os.path.exists(log_path):
        return f"Log file not found at: {log_path}"

    errors = []
    warnings = []
    tracebacks = []

    try:
        in_traceback = False
        current_tb = []
        
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line_str = line.strip()
                # Check for standard levels
                if "[ERROR]" in line:
                    errors.append(line_str)
                elif "[WARNING]" in line:
                    warnings.append(line_str)
                
                # Check for Tracebacks
                if line.startswith("Traceback (most recent call last):"):
                    in_traceback = True
                    current_tb = [line_str]
                elif in_traceback:
                    if line.startswith(" ") or "File \"" in line or line.startswith("  ") or not line_str:
                        current_tb.append(line_str)
                    else:
                        current_tb.append(line_str)
                        tracebacks.append("\n".join(current_tb))
                        in_traceback = False
                        current_tb = []

        summary = [
            "Log Diagnostics Summary:",
            f"  Errors detected: {len(errors)}",
            f"  Warnings detected: {len(warnings)}",
            f"  Tracebacks/Exceptions: {len(tracebacks)}",
            ""
        ]

        if errors:
            summary.append("Recent Errors (up to 5):")
            for e in errors[-5:]:
                summary.append(f"  - {e}")
            summary.append("")

        if warnings:
            summary.append("Recent Warnings (up to 5):")
            for w in warnings[-5:]:
                summary.append(f"  - {w}")
            summary.append("")

        if tracebacks:
            summary.append("Recent Tracebacks (up to 3):")
            for tb in tracebacks[-3:]:
                summary.append(f"---\n{tb}\n---")
            summary.append("")

        return "\n".join(summary)
    except Exception as e:
        return f"Error analyzing logs: {e}"
