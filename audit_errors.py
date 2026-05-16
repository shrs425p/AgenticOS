import os
import ast
import datetime
import subprocess
from collections import Counter
from pathlib import Path

def get_commit_age(filepath, lineno):
    try:
        res = subprocess.check_output(
            ["git", "blame", "-L", f"{lineno},{lineno}", "--line-porcelain", filepath],
            universal_newlines=True,
            stderr=subprocess.DEVNULL
        )
        for line in res.split("\n"):
            if line.startswith("committer-time "):
                timestamp = int(line.split(" ")[1])
                commit_date = datetime.datetime.fromtimestamp(timestamp)
                return (datetime.datetime.now() - commit_date).days
    except Exception:
        return 0
    return 0

def get_yesterday_stats(yesterday_file):
    bare_count = 0
    vague_lines = set()
    if os.path.exists(yesterday_file):
        with open(yesterday_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("- Bare: "):
                    try:
                        bare_count = int(line.split(":")[1].strip())
                    except ValueError:
                        pass
                elif line.startswith("- ") and " - `" in line and ":" in line:
                    vague_lines.add(line.strip())
    return bare_count, vague_lines

def main():
    target_dirs = ["core", "tools"]

    specific_count = 0
    generic_count = 0
    bare_count = 0

    error_messages = []
    vague_messages = []
    sensitive_messages = []

    todos = []

    SENSITIVE_WORDS = ["key", "token", "password"]

    def process_file(filepath):
        nonlocal specific_count, generic_count, bare_count

        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        lines = content.split('\n')
        for i, line in enumerate(lines):
            if "#" in line:
                comment_part = line[line.find("#"):]
                upper_comment = comment_part.upper()
                if any(x in upper_comment for x in ["TODO", "FIXME", "HACK", "XXX"]):
                    age = get_commit_age(filepath, i + 1)
                    todos.append((filepath, i + 1, comment_part, age))

        try:
            tree = ast.parse(content)
        except SyntaxError:
            return

        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    bare_count += 1
                elif isinstance(node.type, ast.Name) and node.type.id == "Exception":
                    generic_count += 1
                else:
                    specific_count += 1

            # Find logging.error, logging.warning, logger.error, print_error
            if isinstance(node, ast.Call):
                func_name = None
                is_error_call = False

                if isinstance(node.func, ast.Name):
                    if node.func.id in ["print_error"]:
                        is_error_call = True
                elif isinstance(node.func, ast.Attribute):
                    if node.func.attr in ["error", "warning", "exception", "critical"]:
                        # Might be self.logger.error, logger.error, logging.error, self.audit.error
                        is_error_call = True

                if is_error_call and node.args:
                    arg_idx = 0
                    # For self.audit.error(self.session_id, "where", "msg") it's index 2
                    if isinstance(node.func, ast.Attribute) and node.func.attr == "error" and len(node.args) >= 3:
                        if isinstance(node.func.value, ast.Attribute) and node.func.value.attr == "audit":
                            arg_idx = 2

                    arg = node.args[arg_idx] if arg_idx < len(node.args) else node.args[-1]
                    msg = None
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                        msg = arg.value
                    elif isinstance(arg, ast.JoinedStr):
                        msg_parts = []
                        for val in arg.values:
                            if isinstance(val, ast.Constant) and isinstance(val.value, str):
                                msg_parts.append(val.value)
                            elif isinstance(val, ast.FormattedValue):
                                msg_parts.append("{var}")
                        msg = " ".join(msg_parts)

                    if msg:
                        # Clean up formatting whitespace for vague checking
                        cleaned_msg = " ".join(msg.split())

                        error_messages.append((filepath, node.lineno, cleaned_msg))
                        word_count = len(cleaned_msg.split())

                        # Vague if less than 5 words OR exactly "error" or "failed" ignoring case
                        if word_count < 5 or cleaned_msg.strip().lower() in ["error", "failed", "error: {var}", "failed: {var}"]:
                            vague_messages.append((filepath, node.lineno, cleaned_msg))

                        if any(word in cleaned_msg.lower() for word in SENSITIVE_WORDS):
                            sensitive_messages.append((filepath, node.lineno))


    for d in target_dirs:
        if not os.path.isdir(d):
            continue
        for root, _, files in os.walk(d):
            for f in files:
                if f.endswith(".py"):
                    process_file(os.path.join(root, f))

    patterns = Counter([msg for _, _, msg in error_messages])
    top_patterns = patterns.most_common(5)

    # Check yesterday's report
    yesterday_date_str = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    yesterday_file = f"docs/daily_logs/error_patterns_{yesterday_date_str}.md"

    yesterday_bare, yesterday_vague_lines = get_yesterday_stats(yesterday_file)

    flagged_messages = []

    if os.path.exists(yesterday_file):
        if bare_count > yesterday_bare:
            flagged_messages.append(f"NEW bare except block introduced today (from {yesterday_bare} to {bare_count})")

        current_vague_lines = set([f"- {fp}:{ln} - `{msg}`" for fp, ln, msg in vague_messages])
        new_vague_lines = current_vague_lines - yesterday_vague_lines
        if new_vague_lines:
            flagged_messages.append("NEW vague error messages introduced today:")
            for line in new_vague_lines:
                flagged_messages.append(f"  {line}")

    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    out_dir = "docs/daily_logs"
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, f"error_patterns_{date_str}.md")

    with open(out_file, "w", encoding="utf-8") as f:
        f.write(f"# Error Patterns - {date_str}\n\n")

        f.write("## Exception Block Summary\n")
        f.write(f"- Specific: {specific_count}\n")
        f.write(f"- Generic: {generic_count}\n")
        f.write(f"- Bare: {bare_count}\n\n")

        f.write("## Top 5 Error Patterns\n")
        for msg, count in top_patterns:
            f.write(f"- `{msg}` (Count: {count})\n")

        f.write("\n## Vague Error Messages\n")
        for fp, ln, msg in vague_messages:
            f.write(f"- {fp}:{ln} - `{msg}`\n")

        f.write("\n## Potentially Sensitive Error Messages\n")
        for fp, ln in sensitive_messages:
            f.write(f"- {fp}:{ln} - [REDACTED]\n")

        f.write("\n## Old TODO/FIXME Comments (> 7 days)\n")
        # Ensure we only list old ones
        old_todos = [t for t in todos if t[3] > 7]
        for fp, ln, comment, age in old_todos:
            f.write(f"- {fp}:{ln} - {comment.strip()} (Age: {age} days)\n")

        health = "GOOD"
        if bare_count > 0 or len(vague_messages) > 10:
            health = "WARNING"
        if len(sensitive_messages) > 0 or bare_count > 10:
            health = "CRITICAL"

        f.write(f"\n## Health: {health}\n")

        if flagged_messages:
            f.write("\n## Flags compared to yesterday\n")
            for msg in flagged_messages:
                f.write(f"- {msg}\n")

    print(f"Generated {out_file}")

if __name__ == "__main__":
    main()
