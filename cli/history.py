#!/usr/bin/env python3
import json
import os
import sys

def main():
    # Attempt to locate data/task_history.json
    # Assume script is run from project root or inside cli
    history_file = os.path.join("data", "task_history.json")
    if not os.path.exists(history_file):
        history_file = os.path.join("..", "data", "task_history.json")
        if not os.path.exists(history_file):
            print(f"Error: Could not find {history_file} or data/task_history.json")
            sys.exit(1)

    try:
        with open(history_file, "r", encoding="utf-8") as f:
            history_data = json.load(f)
    except json.JSONDecodeError:
        print(f"Error: Could not parse {history_file} as JSON.")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading {history_file}: {e}")
        sys.exit(1)

    if not history_data:
        print("Task history is empty.")
        return

    print("="*80)
    print(" TASK HISTORY")
    print("="*80)

    for idx, task in enumerate(history_data, 1):
        print(f"\nTask #{idx}")
        print(f"  ID:       {task.get('task_id', 'N/A')}")
        print(f"  Time:     {task.get('timestamp', 'N/A')}")
        print(f"  Summary:  {task.get('task_summary', 'N/A')}")
        ops = task.get('ops_used', [])
        ops_str = ", ".join(ops) if ops else "None"
        print(f"  Tools:    {ops_str}")
        print(f"  Success:  {task.get('success', 'N/A')}")
        print(f"  Duration: {task.get('duration_seconds', 0):.2f}s")
        print("-" * 80)

if __name__ == "__main__":
    main()
