from unittest.mock import patch, MagicMock
import pytest
from core.resource_profiler import profile_hardware, should_throttle, HardwareProfile

def test_profile_hardware_low():
    # Mock psutil memory to <= 4GB
    mock_mem = MagicMock()
    mock_mem.total = int(3 * (1024 ** 3))
    mock_mem.available = int(1 * (1024 ** 3))
    
    with patch("core.resource_profiler.psutil.virtual_memory", return_value=mock_mem), \
         patch("core.resource_profiler.os.cpu_count", return_value=2):
        
        prof = profile_hardware()
        assert prof.ram_tier == "low"
        assert prof.recommended_max_workers == 2
        assert prof.recommended_context_tokens == 8192
        assert prof.compact_history_threshold == 15

def test_profile_hardware_mid():
    # Mock psutil memory to 8GB
    mock_mem = MagicMock()
    mock_mem.total = int(8 * (1024 ** 3))
    mock_mem.available = int(4 * (1024 ** 3))
    
    with patch("core.resource_profiler.psutil.virtual_memory", return_value=mock_mem), \
         patch("core.resource_profiler.os.cpu_count", return_value=4):
        
        prof = profile_hardware()
        assert prof.ram_tier == "mid"
        assert prof.recommended_max_workers == 4
        assert prof.recommended_context_tokens == 32768
        assert prof.compact_history_threshold == 30

def test_profile_hardware_high():
    # Mock psutil memory to 32GB
    mock_mem = MagicMock()
    mock_mem.total = int(32 * (1024 ** 3))
    mock_mem.available = int(20 * (1024 ** 3))
    
    with patch("core.resource_profiler.psutil.virtual_memory", return_value=mock_mem), \
         patch("core.resource_profiler.os.cpu_count", return_value=8):
        
        prof = profile_hardware()
        assert prof.ram_tier == "high"
        assert prof.recommended_max_workers == 8
        assert prof.recommended_context_tokens == 131072
        assert prof.compact_history_threshold == 60

def test_should_throttle_true():
    mock_mem = MagicMock()
    mock_mem.percent = 85.0
    with patch("core.resource_profiler.psutil.virtual_memory", return_value=mock_mem):
        assert should_throttle() is True

def test_should_throttle_false():
    mock_mem = MagicMock()
    mock_mem.percent = 50.0
    with patch("core.resource_profiler.psutil.virtual_memory", return_value=mock_mem):
        assert should_throttle() is False
