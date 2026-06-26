import os
import psutil
from dataclasses import dataclass

@dataclass
class HardwareProfile:
    ram_tier: str  # "low", "mid", or "high"
    cpu_count: int
    available_ram_gb: float
    total_ram_gb: float
    recommended_max_workers: int
    recommended_context_tokens: int
    recommended_cache_mb: int
    compact_history_threshold: int

def profile_hardware() -> HardwareProfile:
    """Query system resources and return a HardwareProfile configuration recommendation."""
    mem = psutil.virtual_memory()
    total_ram_gb = mem.total / (1024 ** 3)
    available_ram_gb = mem.available / (1024 ** 3)
    cpu_count = os.cpu_count() or psutil.cpu_count(logical=True) or 2

    if total_ram_gb <= 4.0:
        ram_tier = "low"
        recommended_max_workers = 2
        recommended_context_tokens = 8192
        recommended_cache_mb = 128
        compact_history_threshold = 15
    elif total_ram_gb <= 16.0:
        ram_tier = "mid"
        recommended_max_workers = 4
        recommended_context_tokens = 32768
        recommended_cache_mb = 512
        compact_history_threshold = 30
    else:
        ram_tier = "high"
        recommended_max_workers = max(4, cpu_count)
        recommended_context_tokens = 131072
        recommended_cache_mb = 2048
        compact_history_threshold = 60

    return HardwareProfile(
        ram_tier=ram_tier,
        cpu_count=cpu_count,
        available_ram_gb=round(available_ram_gb, 2),
        total_ram_gb=round(total_ram_gb, 2),
        recommended_max_workers=recommended_max_workers,
        recommended_context_tokens=recommended_context_tokens,
        recommended_cache_mb=recommended_cache_mb,
        compact_history_threshold=compact_history_threshold
    )

def should_throttle() -> bool:
    """Return True if memory pressure is high (virtual memory usage > 80%)."""
    mem = psutil.virtual_memory()
    return mem.percent > 80.0
