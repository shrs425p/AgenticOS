import os
import subprocess
import sys
import pytest

VECTOR_MEMORY_PATH = os.path.abspath("tools/plugins/vector_memory.py")

def test_vector_memory_decay_mutation():
    """Verify that mutating the decay factor formula in vector_memory.py causes tests to fail."""
    # 1. Read original content
    with open(VECTOR_MEMORY_PATH, "r", encoding="utf-8") as f:
        original_content = f.read()
        
    target_string = "decay_factor = np.exp(-(np.log(2.0) / 30.0) * dt_days)"
    mutated_string = "decay_factor = np.exp((np.log(2.0) / 30.0) * dt_days)" # removed negative sign
    
    assert target_string in original_content, "Target string for mutation not found in source file!"
    
    mutated_content = original_content.replace(target_string, mutated_string)
    
    try:
        # Write mutated version
        with open(VECTOR_MEMORY_PATH, "w", encoding="utf-8") as f:
            f.write(mutated_content)
            
        # Run pytest on tests/test_vector_memory.py
        cmd = [sys.executable, "-m", "pytest", "tests/test_vector_memory.py", "-k", "test_exponential_time_decay"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # We assert that the test fails (exit code != 0) when the code is mutated
        assert result.returncode != 0, "Test suite did not fail when decay logic was mutated!"
        assert "FAILED" in result.stdout or "FAILED" in result.stderr or "errors" in result.stdout.lower()
        
    finally:
        # Restore original content
        with open(VECTOR_MEMORY_PATH, "w", encoding="utf-8") as f:
            f.write(original_content)


def test_vector_memory_sort_direction_mutation():
    """Verify that negating the similarity search sorting direction causes tests to fail."""
    # 1. Read original content
    with open(VECTOR_MEMORY_PATH, "r", encoding="utf-8") as f:
        original_content = f.read()
        
    target_string = 'results.sort(key=lambda x: x["similarity"], reverse=True)'
    mutated_string = 'results.sort(key=lambda x: x["similarity"], reverse=False)'
    
    assert target_string in original_content, "Target sorting string for mutation not found in source file!"
    
    mutated_content = original_content.replace(target_string, mutated_string)
    
    try:
        # Write mutated version
        with open(VECTOR_MEMORY_PATH, "w", encoding="utf-8") as f:
            f.write(mutated_content)
            
        # Run pytest on tests/test_vector_memory.py
        cmd = [sys.executable, "-m", "pytest", "tests/test_vector_memory.py", "-k", "test_vector_memory_store_and_search"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # We assert that the test fails (exit code != 0) when the code is mutated
        assert result.returncode != 0, "Test suite did not fail when sorting logic was mutated!"
        assert "FAILED" in result.stdout or "FAILED" in result.stderr or "errors" in result.stdout.lower()
        
    finally:
        # Restore original content
        with open(VECTOR_MEMORY_PATH, "w", encoding="utf-8") as f:
            f.write(original_content)
