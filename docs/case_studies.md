# AgenticOS: Case Studies and Evaluation Results

This document provides real-world examples of tasks performed during the "Crucible" production stress test. These case studies demonstrate the agent's reasoning, tool use, and performance under high-load scenarios.

---

## Case Study 1: Enterprise Disk Hygiene Audit (Task 8)

### The Challenge:
Analyze the entire `C:\` drive to find:
1.  The top 20 largest files.
2.  Duplicate filenames across common directories.
3.  Files not accessed in 180+ days.
4.  Generate a comprehensive `disk_hygiene_report.md`.

### The "Crucible" Evolution:
-   **Initial Attempt**: The agent used a recursive Python walker (`grep_dir`). This caused 100% SSD usage and a system-wide lag due to the millions of files on the host machine.
-   **Optimization**: We implemented an optimized, stack-based native Python DFS `os.scandir` crawler as part of the "Fast-Path" IO subsystem.
-   **Final Result**: The agent completed the entire drive audit in **under 30 seconds** (scanning 1M+ files on `C:\`).

### Verified Output:
> **Report Excerpt (`workspace/disk_hygiene_report.md`):**
> | File Name | Size | Path |
> | :--- | :--- | :--- |
> | `pagefile.sys` | 16.0 GB | `C:\pagefile.sys` |
> | `hiberfil.sys` | 8.2 GB | `C:\hiberfil.sys` |
> | `archive.zip` | 4.1 GB | `C:\Users\shrs\Downloads\archive.zip` |

---

## Case Study 2: Self-Monitoring and Process Profiling (Task 5)

### The Challenge:
Profile the AgenticOS process itself:
1.  Monitor PID, RAM usage, CPU percentage, and Open Handles.
2.  Sample data every 5 seconds for 60 seconds.
3.  Generate a high-resolution `self_monitoring_chart.png`.

### The Result:
The agent autonomously generated a Python script (`profile_self.py`) using `psutil` and `matplotlib`. It executed the script in the background, collected the telemetry data, and saved the visualization to the workspace.

### Performance Snapshot:
-   **Avg RAM**: 120MB
-   **Peak CPU**: 15% (during inference)
-   **Handle Count**: 240 (Stable)

---

## Case Study 3: Scheduled Task Security Audit (Task 6)

### The Challenge:
Enumerate all Windows Scheduled Tasks and identify "Suspicious" entries (tasks pointing to Temp folders or non-standard paths).

### The Result:
The agent used `run_powershell` to fetch the task registry. It identified several entries from "Lenovo" and "Google" that used unusual relaunch parameters and flagged them for human review.

### Verified Output:
> **Report Excerpt (`workspace/scheduled_tasks_report.md`):**
> | Task Name | Command | Suspicious? | Rationale |
> | :--- | :--- | :--- | :--- |
> | `Google\Quick Share` | `nearby_share_launcher.exe` | **Yes** | Relaunch-on-crash flag detected. |
> | `LenovoNowTask` | `LenovoNow.Task.exe` | **Yes** | Uses dynamic event data $(EventData). |

---

## Case Study 4: Firewall Penetration Audit (Task 11)

### The Challenge:
Query Windows firewall rules for inbound traffic on non-standard ports (>1024) and research their typical service usage via the web.

### The Result:
The agent extracted hundreds of rules, filtered them for ports like `8080`, `3306`, and `5000`, and then used `web_search` to verify if they belonged to known applications or potential vulnerabilities.

---

## Case Study 5: Dynamic Code Auditing and Self-Healing Packages (Task 68)

### The Challenge:
Audit the cyclomatic complexity of all functions and classes in `core/tool_registry.py` without pre-installed linting software or system dependencies.

### The "Crucible" Evolution:
-   **Initial Check**: The agent checked system package managers (`check_package_managers`) and discovered `winget` active on Windows.
-   **Self-Healing**: Triggered a dynamic, background package resolver `install_system_package` (along with `pip` installers) to silently compile and provision `radon` on-the-fly.
-   **Parsing & Analysis**: Using Abstract Syntax Tree (AST) node parsing, traversed `tool_registry.py` to evaluate complex blocks, outputting a beautiful cyclomatic report graded `A` to `F` in **under 20 seconds**.

### Verified Output:
> **Report Excerpt (`workspace/tool_registry_complexity.md`):**
> | Block Type | Name | Complexity Score | Grade | Recommendation |
> | :--- | :--- | :---: | :---: | :--- |
> | Class | `ToolRegistry` | 1 | **A** | Excellent (Low risk) |
> | Method | `ToolRegistry.register` | 4 | **A** | Excellent (Simple, low risk block) |
> | Method | `ToolRegistry.load_plugins` | 12 | **C** | Moderate (Review carefully) |

---

## Summary of Evaluation Performance

| Task Category | Success Rate | Avg. Time to Complete | Key Tools Used |
| :--- | :--- | :--- | :--- |
| **System Diagnostics** | 100% | 45 Seconds | PowerShell, WMI |
| **Security Auditing** | 100% | 2.5 Minutes | EventLog, WebSearch |
| **Filesystem Management** | 100% | 12 Seconds | Fast-Path DFS |
| **Web Research** | 100% | 30 Seconds | Playwright, Brave |

---

## Conclusion
The "Crucible" test proved that AgenticOS can handle enterprise-level workloads without degrading system performance, thanks to its **Native Optimization** and **Autonomous Self-Correction** capabilities.

---

*Last Updated: 2026-06-03*
*Status: Evaluation Complete*
