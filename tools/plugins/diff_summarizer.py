"""Plugin module for summarizing differences between two texts in plain English."""
import difflib
from core.tool_registry import tool


@tool(name="diff_summarizer", category="Custom")
def summarize_text_diff(old_text: str, new_text: str) -> str:
    """Takes two text strings and returns a detailed, plain-English summary of what changed between them.

    Args:
        old_text (str): The baseline/original text content.
        new_text (str): The updated/target text content.

    Returns:
        str: A highly organized, line-by-line summary of additions, deletions, and modifications.
    """
    old_lines = old_text.splitlines()
    new_lines = new_text.splitlines()

    # Generate standard unified diff to extract delta
    diff = list(difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile="Original",
        tofile="Updated",
        lineterm=""
    ))

    if not diff:
        return "No changes detected. The original and updated texts are identical."

    additions = 0
    deletions = 0
    modifications = 0

    change_log = []

    # Parse unified diff format
    for line in diff:
        if line.startswith("+++") or line.startswith("---") or line.startswith("@@"):
            continue
        if line.startswith("+"):
            additions += 1
            change_log.append(f"Added line: '{line[1:].strip()}'")
        elif line.startswith("-"):
            deletions += 1
            change_log.append(f"Removed line: '{line[1:].strip()}'")

    # Generate modifications heuristic: pairs of close additions & deletions
    total_changes = additions + deletions
    summary_report = [
        "# Text Diff & Modification Summary",
        "",
        f"**Overview of Differences**:",
        f"- Total additions: {additions} line(s)",
        f"- Total deletions: {deletions} line(s)",
        f"- Total lines changed: {total_changes} line(s)",
        "",
        "## Detailed Change Log",
        ""
    ]

    if change_log:
        summary_report.extend([f"- {log}" for log in change_log])
    else:
        summary_report.append("- No specific line-level additions or deletions were isolated.")

    return "\n".join(summary_report)
