"""Module for self_healing_test.py"""
import datetime
import json
from pathlib import Path
from core.tool_registry import tool
from core.runtime_config import DEFAULT_WORKSPACE

@tool(name="self_healing_test", desc="Runs daily self-healing tests, validating recovery logic.", category="System")
def self_healing_test() -> str:
    """Runs daily self-healing tests, validating recovery logic."""
    target_file = Path(DEFAULT_WORKSPACE) / "healing_test_target.txt"
    log_dir = Path(DEFAULT_WORKSPACE) / "daily_logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    log_file = log_dir / f"self_healing_{today}.md"

    result = {
        "steps": [],
        "outcome": "success",
        "recovery_actions": []
    }

    try:
        # Step 1: Read the file
        try:
            target_file.read_text()
            result["steps"].append("File found initially, this shouldn't happen usually.")
        except FileNotFoundError:
            result["steps"].append("File missing, starting recovery.")
            result["recovery_actions"].append("Catch FileNotFoundError")

            # Step 2: Create the file
            target_file.write_text("Created by self-healing recovery")
            result["recovery_actions"].append("Create the file")

            # Step 3: Verify the file exists and is readable
            content = target_file.read_text()
            if content == "Created by self-healing recovery":
                result["recovery_actions"].append("Verify file exists and is readable")
            else:
                raise Exception("File content mismatch")

            # Step 4: Delete the file after verification
            target_file.unlink()
            result["recovery_actions"].append("Delete the file after verification")

    except Exception as e:
        result["outcome"] = "failure"
        result["steps"].append(f"[ERROR] Failed during recovery steps: {e}")

    log_content = (
        f"# Self Healing Test ({today})\n\n"
        f"**Outcome:** {result['outcome']}\n\n"
        f"**Steps:**\n" + "\n".join(f"- {s}" for s in result['steps']) + "\n\n"
        "**Recovery Actions:**\n" + "\n".join(f"- {a}" for a in result['recovery_actions']) + "\n"
    )

    try:
        log_file.write_text(log_content)
    except Exception as e:
        print(f"Failed to write log file: {e}")
        result["outcome"] = "failure"

    return json.dumps(result)
