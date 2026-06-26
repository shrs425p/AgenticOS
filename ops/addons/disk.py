"""Module for fast_disk.py"""
import os
import heapq
from collections import defaultdict
from datetime import datetime, timedelta
from kernel.registry import tool
from kernel.ui import C

@tool(
    name="fastdiskaudit",
    desc="Optimized disk analysis using native Python. Finds large files, duplicates, and old files in seconds.",
    category="Files"
)
def fastdiskaudit(path: str | None = None, top_n: int = 20, min_mb: int = 100, mode: str = "all") -> str:
    """
    Performs a high-speed disk audit.
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

    min_bytes = min_mb * 1024 * 1024
    cutoff_date = datetime.now() - timedelta(days=180)
    cutoff_timestamp = cutoff_date.timestamp()

    # Determine paths to scan
    # For duplicate detection on root drive, only scan 'Users' directory to avoid system clutter
    scan_path = os.path.join(path, "Users") if path == os.path.abspath(os.sep) else path

    # If the user only wants duplicates, we can restrict the traversal to scan_path for speed
    start_path = scan_path if mode == "duplicates" else path

    large_files = [] # min-heap of (size, path)
    duplicates = defaultdict(list)
    old_files = [] # list of (access_time, path)

    # Perform traversal
    stack = [start_path]
    while stack:
        curr_dir = stack.pop()
        try:
            with os.scandir(curr_dir) as it:
                for entry in it:
                    try:
                        # Skip symlinks and NTFS junction points/reparse points to avoid loops
                        is_reparse = False
                        if entry.is_symlink():
                            is_reparse = True
                        else:
                            # Verify if it has reparse attribute (NTFS junctions)
                            stat_val = entry.stat(follow_symlinks=False)
                            if hasattr(stat_val, 'st_file_attributes') and (stat_val.st_file_attributes & 0x400):
                                is_reparse = True
                        
                        if is_reparse:
                            continue

                        if entry.is_file():
                            stat_val = entry.stat()
                            
                            # 1. Large files check (if mode requires it)
                            if mode in ("all", "large"):
                                size = stat_val.st_size
                                if size >= min_bytes:
                                    if len(large_files) < top_n:
                                        heapq.heappush(large_files, (size, entry.path))
                                    else:
                                        if size > large_files[0][0]:
                                            heapq.heapreplace(large_files, (size, entry.path))

                            # 2. Duplicate filenames check (if mode requires it)
                            if mode in ("all", "duplicates"):
                                # If mode is 'all', only record duplicates if file is under scan_path
                                # If mode is 'duplicates', start_path is already scan_path
                                if mode == "duplicates" or entry.path.startswith(scan_path):
                                    duplicates[entry.name].append(entry.path)

                            # 3. Old files check (if mode requires it)
                            if mode in ("all", "old"):
                                if stat_val.st_atime < cutoff_timestamp:
                                    old_files.append((stat_val.st_atime, entry.path))

                        elif entry.is_dir():
                            stack.append(entry.path)
                    except Exception:
                        pass
        except Exception:
            pass

    results = []

    if mode in ("all", "large"):
        results.append(f"\n{C.CYAN}--- TOP {top_n} LARGEST FILES ---{C.RESET}")
        top_large = sorted(large_files, key=lambda x: x[0], reverse=True)
        if not top_large:
            results.append("No files found matching the criteria.")
        else:
            col1_header = "Size(GB)"
            col2_header = "FullName"
            rows = []
            max_size_len = len(col1_header)
            for size, file_path in top_large:
                size_gb_str = f"{size / (1024**3):.4f}"
                max_size_len = max(max_size_len, len(size_gb_str))
                rows.append((size_gb_str, file_path))
            
            results.append(f"{col1_header:<{max_size_len}} {col2_header}")
            results.append(f"{'-' * max_size_len} {'-' * len(col2_header)}")
            for size_str, file_path in rows:
                results.append(f"{size_str:<{max_size_len}} {file_path}")

    if mode in ("all", "duplicates"):
        results.append(f"\n{C.CYAN}--- DUPLICATE FILENAMES IN COMMON DIRS ---{C.RESET}")
        dupes_list = [(name, paths) for name, paths in duplicates.items() if len(paths) > 1]
        dupes_list.sort(key=lambda x: len(x[1]), reverse=True)
        top_dupes = dupes_list[:10]

        if not top_dupes:
            results.append("No duplicate filenames found.")
        else:
            col1_header = "Name"
            col2_header = "Count"
            col3_header = "Paths"
            max_name_len = len(col1_header)
            max_count_len = len(col2_header)
            rows = []
            for name, paths in top_dupes:
                count_str = str(len(paths))
                paths_str = "; ".join(paths)
                max_name_len = max(max_name_len, len(name))
                max_count_len = max(max_count_len, len(count_str))
                rows.append((name, count_str, paths_str))
            
            results.append(f"{col1_header:<{max_name_len}} {col2_header:<{max_count_len}} {col3_header}")
            results.append(f"{'-' * max_name_len} {'-' * max_count_len} {'-' * len(col3_header)}")
            for name, count_str, paths_str in rows:
                results.append(f"{name:<{max_name_len}} {count_str:<{max_count_len}} {paths_str}")

    if mode in ("all", "old"):
        results.append(f"\n{C.CYAN}--- FILES NOT ACCESSED IN 180+ DAYS ---{C.RESET}")
        old_files.sort(key=lambda x: x[0])
        top_old = old_files[:10]

        if not top_old:
            results.append("No old files found.")
        else:
            col1_header = "LastAccessTime"
            col2_header = "FullName"
            rows = []
            max_time_len = len(col1_header)
            for acc_time, file_path in top_old:
                try:
                    dt_str = datetime.fromtimestamp(acc_time).strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    dt_str = str(acc_time)
                max_time_len = max(max_time_len, len(dt_str))
                rows.append((dt_str, file_path))
            
            results.append(f"{col1_header:<{max_time_len}} {col2_header}")
            results.append(f"{'-' * max_time_len} {'-' * len(col2_header)}")
            for dt_str, file_path in rows:
                results.append(f"{dt_str:<{max_time_len}} {file_path}")

    return "\n".join(results)
