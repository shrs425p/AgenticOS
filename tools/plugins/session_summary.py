import sqlite3
import datetime
import logging
import re
from pathlib import Path
from core.tool_registry import tool

logger = logging.getLogger(__name__)

@tool(category="System", desc="Generates a daily session summary from logs and evaluation output")
def generate_session_summary():
    """Reads evaluation_output.txt and SQLite audit logs from data/ (if they exist),
    counts total tools called, unique tools used, errors logged, warnings logged,
    identifies the longest-running task, and writes the summary to workspace/daily_logs/."""

    data_dir = Path("data")
    workspace_dir = Path("workspace/daily_logs")

    eval_txt_path = data_dir / "evaluation_output.txt"
    sqlite_files = list(data_dir.glob("*.db")) + list(data_dir.glob("*.sqlite*"))

    missing_eval = not eval_txt_path.exists()
    missing_sqlite = len(sqlite_files) == 0

    if missing_eval and missing_sqlite:
        today = datetime.date.today().isoformat()
        out_file = workspace_dir / f"session_summary_{today}.md"
        workspace_dir.mkdir(parents=True, exist_ok=True)
        try:
            with open(out_file, "w", encoding="utf-8") as f:
                f.write("no session data found\n")
            return "no session data found"
        except Exception as e:
            return f"Error writing summary: {e}"

    if missing_eval:
        logger.warning(f"Evaluation output file {eval_txt_path} not found.")

    if missing_sqlite:
        logger.warning("No SQLite databases found in data/")

    total_tools = 0
    unique_tools = set()
    errors = 0
    warnings = 0
    longest_task = "N/A"
    longest_duration = -1

    if not missing_eval:
        try:
            with open(eval_txt_path, "r", encoding="utf-8") as f:
                content = f.read()
                # Dummy parse: count occurrences of "Warning" or "Error" as a fallback
                # Real implementation would depend on exact file structure
                warnings += len(re.findall(r'(?i)\bwarning\b', content))
                errors += len(re.findall(r'(?i)\berror\b', content))
        except Exception as e:
            logger.warning(f"Failed to read evaluation_output.txt: {e}")

    for db_path in sqlite_files:
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Count tools
            try:
                cursor.execute("SELECT tool_name FROM tool_events")
                for row in cursor.fetchall():
                    tool_name = row[0]
                    if tool_name:
                        total_tools += 1
                        unique_tools.add(tool_name)
            except sqlite3.OperationalError:
                pass # table might not exist

            # Count errors/warnings from messages or similar
            try:
                cursor.execute("SELECT content FROM messages")
                for row in cursor.fetchall():
                    content = row[0]
                    if content:
                        if re.search(r'(?i)\berror\b', content):
                            errors += 1
                        if re.search(r'(?i)\bwarning\b', content):
                            warnings += 1
            except sqlite3.OperationalError:
                pass

            # Find longest task
            try:
                # Assuming 'tasks' table structure with created_at and updated_at
                cursor.execute("SELECT task_id, created_at, updated_at FROM tasks")
                for row in cursor.fetchall():
                    task_id, created_at, updated_at = row
                    if created_at and updated_at:
                        try:
                            start = datetime.datetime.fromisoformat(created_at)
                            end = datetime.datetime.fromisoformat(updated_at)
                            duration = (end - start).total_seconds()
                            if duration > longest_duration:
                                longest_duration = duration
                                longest_task = task_id
                        except ValueError:
                            pass
            except sqlite3.OperationalError:
                pass

            conn.close()
        except Exception as e:
            logger.warning(f"Failed to read SQLite DB {db_path}: {e}")

    today = datetime.date.today().isoformat()
    out_file = workspace_dir / f"session_summary_{today}.md"
    workspace_dir.mkdir(parents=True, exist_ok=True)

    summary = [
        f"# Session Summary for {today}",
        "",
        f"- **Total Tools Called**: {total_tools}",
        f"- **Unique Tools Used**: {len(unique_tools)}",
        f"- **Errors Logged**: {errors}",
        f"- **Warnings Logged**: {warnings}",
        f"- **Longest Running Task**: {longest_task} (Duration: {longest_duration if longest_duration >= 0 else 'N/A'}s)"
    ]

    summary_text = "\n".join(summary)

    try:
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(summary_text)
        return f"Summary written to {out_file}"
    except Exception as e:
        return f"Error writing summary: {e}"

if __name__ == "__main__":
    print(generate_session_summary())