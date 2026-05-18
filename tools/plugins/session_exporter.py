"""Session export plugin for AgenticOs.

Exports the current session's full conversation, tool calls, and results to:
- JSON: structured export with all events and timestamps
- HTML: self-contained single-file report with collapsible tool sections
- PDF: rendered via weasyprint (optional, gracefully degraded to HTML)
"""

import json
import os
from datetime import datetime

from core.tool_registry import tool


def _get_session_data(db_path: str, session_id: str) -> dict:
    """Retrieve session data from the SQLite memory database."""
    import sqlite3

    data = {
        "session_id": session_id,
        "messages": [],
        "tool_events": [],
        "tasks": [],
        "outcomes": [],
        "exported_at": datetime.now().isoformat(),
    }

    if not os.path.exists(db_path):
        return data

    try:
        conn = sqlite3.connect(db_path, timeout=5, check_same_thread=False)

        cur = conn.execute(
            "SELECT role, content, created_at FROM messages WHERE session_id=? ORDER BY id ASC",
            (session_id,),
        )
        data["messages"] = [
            {"role": r, "content": c, "created_at": ts} for r, c, ts in cur.fetchall()
        ]

        cur = conn.execute(
            "SELECT tool_name, tool_args, observation, created_at FROM tool_events WHERE session_id=? ORDER BY id ASC",
            (session_id,),
        )
        data["tool_events"] = [
            {"tool": t, "args": a, "observation": o, "created_at": ts}
            for t, a, o, ts in cur.fetchall()
        ]

        cur = conn.execute(
            "SELECT task_id, goal, status, created_at, final_answer FROM tasks WHERE session_id=? ORDER BY rowid ASC",
            (session_id,),
        )
        data["tasks"] = [
            {"task_id": tid, "goal": g, "status": s, "created_at": ts, "final_answer": fa}
            for tid, g, s, ts, fa in cur.fetchall()
        ]

        cur = conn.execute(
            "SELECT final_answer, next_steps, updated_at FROM outcomes WHERE session_id=?",
            (session_id,),
        )
        row = cur.fetchone()
        if row:
            data["outcomes"] = [{"final_answer": row[0], "next_steps": row[1], "updated_at": row[2]}]

        conn.close()
    except Exception as exc:
        data["_error"] = str(exc)

    return data


def _build_html(data: dict) -> str:
    """Build a self-contained HTML report from session data."""
    session_id = data.get("session_id", "unknown")
    exported_at = data.get("exported_at", "")
    messages = data.get("messages", [])
    tool_events = data.get("tool_events", [])
    tasks = data.get("tasks", [])

    def _esc(s: str) -> str:
        return (
            str(s)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    msg_html = ""
    for m in messages:
        role = m.get("role", "user")
        content = _esc(m.get("content", ""))
        ts = _esc(m.get("created_at", ""))
        bg = "#1e3a5f" if role == "assistant" else "#2d2d2d"
        msg_html += f'<div class="msg {role}" style="background:{bg}"><span class="role">{_esc(role)}</span><span class="ts">{ts}</span><pre>{content}</pre></div>\n'

    tool_html = ""
    for i, ev in enumerate(tool_events):
        tool_name = _esc(ev.get("tool", "?"))
        args = _esc(ev.get("args", ""))
        obs = _esc(ev.get("observation", ""))
        ts = _esc(ev.get("created_at", ""))
        tool_html += f"""<details><summary>[{i+1}] <b>{tool_name}</b> <span class="ts">{ts}</span></summary>
<pre class="args">{args}</pre>
<pre class="obs">{obs}</pre>
</details>\n"""

    task_html = ""
    for t in tasks:
        goal = _esc(t.get("goal", ""))
        status = _esc(t.get("status", ""))
        fa = _esc(t.get("final_answer", ""))
        color = "#4caf50" if status == "completed" else "#f44336"
        task_html += f'<div class="task"><b style="color:{color}">{status}</b> — {goal}<pre>{fa}</pre></div>\n'

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>AgenticOs Session — {_esc(session_id)}</title>
<style>
  body {{ background: #1a1a1a; color: #e0e0e0; font-family: monospace; margin: 20px; }}
  h1, h2 {{ color: #00bcd4; }}
  .msg {{ border-left: 3px solid #00bcd4; padding: 8px 12px; margin: 6px 0; border-radius: 4px; }}
  .msg.user {{ border-color: #66bb6a; }}
  .msg .role {{ font-weight: bold; color: #00bcd4; margin-right: 10px; }}
  .msg.user .role {{ color: #66bb6a; }}
  .ts {{ font-size: 0.75em; color: #888; }}
  pre {{ white-space: pre-wrap; word-break: break-word; margin: 4px 0; }}
  details {{ background: #2a2a2a; padding: 6px 10px; margin: 4px 0; border-radius: 4px; }}
  summary {{ cursor: pointer; color: #ffa726; }}
  .args {{ color: #90caf9; }}
  .obs {{ color: #a5d6a7; }}
  .task {{ background: #263238; padding: 8px 12px; margin: 6px 0; border-radius: 4px; }}
  hr {{ border-color: #444; }}
</style>
</head>
<body>
<h1>AgenticOs Session Report</h1>
<p><b>Session ID:</b> {_esc(session_id)}<br>
<b>Exported:</b> {_esc(exported_at)}</p>
<hr>
<h2>Tasks ({len(tasks)})</h2>
{task_html or "<p>No tasks recorded.</p>"}
<hr>
<h2>Messages ({len(messages)})</h2>
{msg_html or "<p>No messages recorded.</p>"}
<hr>
<h2>Tool Events ({len(tool_events)})</h2>
{tool_html or "<p>No tool events recorded.</p>"}
</body>
</html>"""
    return html


@tool(
    name="export_session",
    desc="Export the current session to JSON, HTML, or PDF. Args: format ('json'|'html'|'pdf'), output_path (optional file path).",
    category="system",
    version="1.0.0",
)
def export_session(format: str = "html", output_path: str = "") -> str:
    """Export the current session's conversation and tool calls.

    Args:
        format: Export format — 'json', 'html', or 'pdf'.
        output_path: Destination file path. Defaults to workspace/session_export.<ext>.

    Returns:
        Path to the exported file, or an error message.
    """
    # Locate the memory database
    workspace = os.environ.get("AGENTICOS_WORKSPACE", "workspace")
    db_path = os.path.join(workspace, "memory.sqlite3")

    # Determine session_id from the most recent session
    session_id = _find_latest_session(db_path)

    data = _get_session_data(db_path, session_id)

    fmt = format.strip().lower()
    if fmt not in ("json", "html", "pdf"):
        return f"Error: unsupported format '{format}'. Choose json, html, or pdf."

    if not output_path:
        export_dir = os.path.join(workspace, "exports")
        os.makedirs(export_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(export_dir, f"session_{ts}.{fmt if fmt != 'pdf' else 'html'}")

    try:
        if fmt == "json":
            with open(output_path, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2, ensure_ascii=False)
            return f"Session exported to JSON: {output_path}"

        elif fmt in ("html", "pdf"):
            html_content = _build_html(data)

            if fmt == "html":
                with open(output_path, "w", encoding="utf-8") as fh:
                    fh.write(html_content)
                return f"Session exported to HTML: {output_path}"

            # PDF via weasyprint (optional)
            pdf_path = output_path.replace(".html", ".pdf")
            if pdf_path == output_path:
                pdf_path = output_path + ".pdf"
            try:
                from weasyprint import HTML as WeasyprintHTML

                WeasyprintHTML(string=html_content).write_pdf(pdf_path)
                return f"Session exported to PDF: {pdf_path}"
            except ImportError:
                # Graceful degradation: write HTML instead
                html_path = output_path if output_path.endswith(".html") else output_path + ".html"
                with open(html_path, "w", encoding="utf-8") as fh:
                    fh.write(html_content)
                return (
                    f"weasyprint not installed; exported as HTML instead: {html_path}\n"
                    "Install weasyprint for PDF support: pip install weasyprint"
                )
    except Exception as exc:
        return f"Export failed: {exc}"

    return f"Export complete: {output_path}"


def _find_latest_session(db_path: str) -> str:
    """Return the most recent session_id from the database, or a fallback."""
    try:
        import sqlite3

        conn = sqlite3.connect(db_path, timeout=5, check_same_thread=False)
        cur = conn.execute(
            "SELECT session_id FROM sessions ORDER BY updated_at DESC LIMIT 1"
        )
        row = cur.fetchone()
        conn.close()
        if row:
            return row[0]
    except Exception:
        pass
    return datetime.now().strftime("%Y%m%d_%H%M%S")
