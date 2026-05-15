import subprocess
import os
from core.tool_registry import tool
from core.runtime_ui import C

@tool(
    name="fast_disk_audit",
    desc="Optimized disk analysis using native PowerShell. Finds large files, duplicates, and old files in seconds.",
    category="Files"
)
def fast_disk_audit(path: str = None, top_n: int = 20, min_mb: int = 100, mode: str = "all"):
    """
    Performs a high-speed disk audit using PowerShell.
    Modes: 'large' (top files), 'duplicates' (duplicate filenames), 'old' (not accessed in 180d), 'all'.
    """
    if path is None:
        path = os.path.abspath(os.sep)
    allowed_modes = {"large", "duplicates", "old", "all"}
    mode = (mode or "all").strip().lower()
    if mode not in allowed_modes:
        return f"Error: mode must be one of {', '.join(sorted(allowed_modes))}."

    try:
        top_n = max(1, min(int(top_n), 200))
    except Exception:
        top_n = 20
    try:
        min_mb = max(0, int(min_mb))
    except Exception:
        min_mb = 100

    results = []

    def ps_literal(value: str) -> str:
        return "'" + str(value).replace("'", "''") + "'"
    
    def run_ps(cmd):
        try:
            res = subprocess.check_output(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd],
                shell=False,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            return res.strip()
        except subprocess.CalledProcessError as e:
            return f"Error: {e.output}"
        except Exception as e:
            return f"Error: {e}"

    if mode in ("all", "large"):
        results.append(f"\n{C.CYAN}--- TOP {top_n} LARGEST FILES ---{C.RESET}")
        # Securely escape single quotes for PowerShell
        safe_path = path.replace("'", "''")
        cmd = (
            f"Get-ChildItem -Path '{safe_path}' -File -Recurse -ErrorAction SilentlyContinue | "
            f"Sort-Object Length -Descending | Select-Object -First {top_n} | "
            "Select-Object @{Name='Size(GB)';Expression={$_.Length / 1GB}}, FullName"
        )
        results.append(run_ps(cmd))

    if mode in ("all", "duplicates"):
        results.append(f"\n{C.CYAN}--- DUPLICATE FILENAMES IN COMMON DIRS ---{C.RESET}")
        # Focus on user dirs to avoid system junk duplicates
        scan_path = os.path.join(path, "Users") if path == os.path.abspath(os.sep) else path
        safe_scan_path = scan_path.replace("'", "''")
        cmd = (
            f"Get-ChildItem -Path '{safe_scan_path}' -File -Recurse -ErrorAction SilentlyContinue | "
            "Group-Object Name | Where-Object { $_.Count -gt 1 } | Select-Object -First 10 | "
            "Select-Object Name, Count, @{Name='Paths';Expression={($_.Group.FullName -join '; ')}}"
        )
        results.append(run_ps(cmd))

    if mode in ("all", "old"):
        results.append(f"\n{C.CYAN}--- FILES NOT ACCESSED IN 180+ DAYS ---{C.RESET}")
        # We'll use a PS command for this too
        safe_path = path.replace("'", "''")
        cmd = (
            f"Get-ChildItem -Path '{safe_path}' -File -Recurse -ErrorAction SilentlyContinue | "
            f"Where-Object {{ $_.LastAccessTime -lt (Get-Date).AddDays(-180) }} | "
            f"Select-Object -First 10 | Select-Object LastAccessTime, FullName"
        )
        results.append(run_ps(cmd))

    return "\n".join(results)
