"""Module for system_benchmark.py"""
from __future__ import annotations

import os
import time
import hashlib
from concurrent.futures import ThreadPoolExecutor
from kernel.registry import tool

def _get_cache_dir() -> str:
    """Helper to resolve the local data/cache directory."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    cache_dir = os.path.join(base_dir, "data", "cache")
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir

@tool(
    name="benchmarkdisk",
    desc="Benchmark local disk write and read performance. Args: size_mb (int, optional).",
    category="Diagnostics"
)
def benchmarkdisk(size_mb: int = 20) -> str:
    """Measures sequential disk write and read throughput (MB/s) in the data/cache directory."""
    try:
        mb = max(1, min(int(size_mb), 100))
    except Exception:
        mb = 20

    cache_dir = _get_cache_dir()
    temp_file = os.path.join(cache_dir, f".__benchmark_test_{int(time.time())}")
    
    # 1MB chunk of dummy bytes
    chunk = b"X" * (1024 * 1024)
    
    try:
        # Write test
        t0 = time.perf_counter()
        with open(temp_file, "wb") as f:
            for _ in range(mb):
                f.write(chunk)
                f.flush()
                os.fsync(f.fileno())
        write_time = time.perf_counter() - t0
        write_speed = mb / write_time if write_time > 0 else 0.0

        # Read test
        t1 = time.perf_counter()
        read_bytes = 0
        with open(temp_file, "rb") as f:
            while True:
                data = f.read(1024 * 1024)
                if not data:
                    break
                read_bytes += len(data)
        read_time = time.perf_counter() - t1
        read_speed = mb / read_time if read_time > 0 else 0.0

        # Cleanup
        if os.path.exists(temp_file):
            os.remove(temp_file)

        return (
            f"Sequential Disk Benchmark ({mb} MB file):\n"
            f"  - Write Speed: {write_speed:.2f} MB/s (took {write_time:.4f} seconds)\n"
            f"  - Read Speed:  {read_speed:.2f} MB/s (took {read_time:.4f} seconds)"
        )
    except Exception as e:
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except Exception:
                pass
        return f"Disk benchmark error: {e}"

def _run_cpu_workload() -> int:
    """Helper representing a heavy CPU hashing workload."""
    base_data = b"AgenticOS raw performance testing chunk data" * 100
    iterations = 25000
    for _ in range(iterations):
        hashlib.sha256(base_data).hexdigest()
    return iterations

@tool(
    name="benchmarkcpu",
    desc="Benchmark host CPU multi-threaded compute performance. Args: threads (int, optional).",
    category="Diagnostics"
)
def benchmarkcpu(threads: int = 4) -> str:
    """Measures multi-threaded CPU hashing capabilities and reports hashes per second."""
    try:
        num_threads = max(1, min(int(threads), 16))
    except Exception:
        num_threads = 4

    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(_run_cpu_workload) for _ in range(num_threads)]
        total_hashes = sum(f.result() for f in futures)
    
    elapsed = time.perf_counter() - t0
    hashes_per_sec = total_hashes / elapsed if elapsed > 0 else 0.0

    return (
        f"Multi-Threaded CPU Hashing Benchmark ({num_threads} worker thread(s)):\n"
        f"  - Total SHA-256 Hashes Computed: {total_hashes:,}\n"
        f"  - Benchmark Execution Time:     {elapsed:.4f} seconds\n"
        f"  - Hashing Throughput:           {hashes_per_sec:,.2f} hashes/sec"
    )
