#!/usr/bin/env python3
"""Sentinel monitor script.

Continuously watches the AgenticOs log file (agent.log) for lines that contain
the keywords "ERROR" or "CRITICAL" and prints an alert message when such a line
is detected.

Usage:
    python -u scripts/sentinel.py   # -u for unbuffered output (real‑time)
"""

import os
import time
import sys

# Path to the log file – adjust if the log location changes.
LOG_PATH = os.path.join(os.path.dirname(__file__), "..", "agent.log")


def tail_f(filepath):
    """Yield new lines as they are appended to *filepath* (similar to `tail -f`)."""
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        # Move to the end of the file so we only see new entries.
        f.seek(0, os.SEEK_END)
        while True:
            line = f.readline()
            if not line:
                # No new line – pause briefly.
                time.sleep(0.5)
                continue
            yield line.rstrip("\n")


def main():
    if not os.path.isfile(LOG_PATH):
        print(f"[Sentinel] Log file not found: {LOG_PATH}", file=sys.stderr)
        sys.exit(1)
    print(f"[Sentinel] Monitoring {LOG_PATH} for ERROR/CRITICAL entries...")
    for line in tail_f(LOG_PATH):
        if "ERROR" in line or "CRITICAL" in line:
            # Simple alert – could be extended to send a desktop notification.
            print(f"[Sentinel ALERT] {line}")
            # Write alert to dedicated log file
            alert_log_path = r"C:\\AgenticOs\\sentinel_alerts.log"
            try:
                with open(alert_log_path, "a", encoding="utf-8") as alert_f:
                    alert_f.write(f"{line}\n")
            except Exception as e:
                print(f"[Sentinel] Failed to write alert log: {e}")
            # Attempt desktop notification; fallback to print if unavailable
            try:
                from core.runtime_ui import send_notification

                send_notification(title="AgenticOs Alert", message=line)
            except Exception:
                # If the notification tool cannot be imported, just print
                print(f"[Sentinel] Notification: {line}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[Sentinel] Stopped by user.")
        sys.exit(0)
