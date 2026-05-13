import subprocess
import os
import time
from core.tool_registry import tool
from core.runtime_ui import C

@tool(
    name="fast_disk_audit",
    desc="Optimized disk analysis using native PowerShell. Finds large files, duplicates, and old files in seconds.",
    category="Files"
)
def fast_disk_audit(path: str = "C:\\", top_n: int = 20, min_mb: int = 100, mode: str = "all"):
    """
    Performs a high-speed disk audit using PowerShell.
    Modes: 'large' (top files), 'duplicates' (duplicate filenames), 'old' (not accessed in 180d), 'all'.
    """
    results = []
    
    def run_ps(cmd):
        try:
            # Use -NoProfile and -NonInteractive for speed and stability
            full_cmd = f"powershell -NoProfile -NonInteractive -Command \"{cmd}\""
            res = subprocess.check_output(full_cmd, shell=True, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')
            return res.strip()
        except subprocess.CalledProcessError as e:
            return f"Error: {e.output}"
        except Exception as e:
            return f"Error: {e}"

    if mode in ("all", "large"):
        results.append(f"\n{C.CYAN}--- TOP {top_n} LARGEST FILES ---{C.RESET}")
        cmd = (
            f"Get-ChildItem -Path '{path}' -File -Recurse -ErrorAction SilentlyContinue | "
            f"Sort-Object Length -Descending | Select-Object -First {top_n} | "
            "Select-Object @{Name='Size(GB)';Expression={$_.Length / 1GB}}, FullName"
        )
        results.append(run_ps(cmd))

    if mode in ("all", "duplicates"):
        results.append(f"\n{C.CYAN}--- DUPLICATE FILENAMES IN COMMON DIRS ---{C.RESET}")
        # Focus on user dirs to avoid system junk duplicates
        scan_path = os.path.join(path, "Users") if path == "C:\\" else path
        cmd = (
            f"Get-ChildItem -Path '{scan_path}' -File -Recurse -ErrorAction SilentlyContinue | "
            "Group-Object Name | Where-Object { $_.Count -gt 1 } | Select-Object -First 10 | "
            "Select-Object Name, Count, @{Name='Paths';Expression={($_.Group.FullName -join '; ')}}"
        )
        results.append(run_ps(cmd))

    if mode in ("all", "old"):
        results.append(f"\n{C.CYAN}--- FILES NOT ACCESSED IN 180+ DAYS ---{C.RESET}")
        cutoff = (time.time() - (180 * 86400))
        # We'll use a PS command for this too
        cmd = (
            f"Get-ChildItem -Path '{path}' -File -Recurse -ErrorAction SilentlyContinue | "
            f"Where-Object {{ $_.LastAccessTime -lt (Get-Date).AddDays(-180) }} | "
            f"Select-Object -First 10 | Select-Object LastAccessTime, FullName"
        )
        results.append(run_ps(cmd))

    return "\n".join(results)
