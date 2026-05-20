import os
from tools.plugins.system_benchmark import benchmark_disk, benchmark_cpu, _get_cache_dir

def test_get_cache_dir():
    cache_dir = _get_cache_dir()
    assert os.path.exists(cache_dir)
    assert cache_dir.endswith(os.path.join("data", "cache"))

def test_benchmark_disk():
    # Run with small size to be fast
    res = benchmark_disk(size_mb=1)
    assert "Sequential Disk Benchmark" in res
    assert "Write Speed" in res
    assert "Read Speed" in res

def test_benchmark_cpu():
    res = benchmark_cpu(threads=2)
    assert "Multi-Threaded CPU Hashing Benchmark" in res
    assert "Hashing Throughput" in res
