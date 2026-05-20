"""Unit tests for the vector memory plugin."""

import os
import json
import pytest
from unittest.mock import patch

from tools.plugins.vector_memory import (
    vector_memory_store,
    vector_memory_search,
    VectorDB,
    HAS_NUMPY,
    VECTOR_DIR
)


@pytest.fixture
def test_namespace():
    """Returns a test namespace and cleans up any existing db file."""
    namespace = "test_vectors"
    db_path = os.path.join(VECTOR_DIR, f"{namespace}.json")
    
    if os.path.exists(db_path):
        os.remove(db_path)
        
    yield namespace
    
    if os.path.exists(db_path):
        os.remove(db_path)


def mock_get_embedding(self, text: str):
    """Mock embedding generator. 
    Returns deterministic vectors based on text content to test cosine similarity.
    """
    if "apple" in text.lower():
        return [1.0, 0.0, 0.0]
    elif "banana" in text.lower():
        return [0.9, 0.1, 0.0]
    elif "car" in text.lower():
        return [0.0, 1.0, 0.0]
    elif "truck" in text.lower():
        return [0.0, 0.9, 0.1]
    else:
        return [0.0, 0.0, 1.0]


@pytest.mark.skipif(not HAS_NUMPY, reason="numpy is not installed")
@patch.object(VectorDB, 'get_embedding', new=mock_get_embedding)
def test_vector_memory_store_and_search(test_namespace):
    # Store test records
    res1 = vector_memory_store(test_namespace, "I like eating an apple", metadata="fruit")
    assert "Successfully stored" in res1
    
    vector_memory_store(test_namespace, "Driving a fast car", metadata="vehicle")
    vector_memory_store(test_namespace, "A large truck on the highway", metadata="vehicle")
    vector_memory_store(test_namespace, "Peeling a banana", metadata="fruit")
    
    # Search for fruit-related text
    search_res = vector_memory_search(test_namespace, "apple", top_k=2)
    results = json.loads(search_res)
    
    assert len(results) == 2
    # The exact match should have highest similarity (1.0)
    assert "apple" in results[0]["text"].lower()
    # The related concept should be second (0.9)
    assert "banana" in results[1]["text"].lower()


@pytest.mark.skipif(not HAS_NUMPY, reason="numpy is not installed")
@patch.object(VectorDB, 'get_embedding', new=mock_get_embedding)
def test_vector_memory_search_empty(test_namespace):
    res = vector_memory_search(test_namespace, "apple")
    assert "No records found" in res


@pytest.mark.skipif(not HAS_NUMPY, reason="numpy is not installed")
@patch.object(VectorDB, 'get_embedding', new=mock_get_embedding)
def test_vector_memory_persistence(test_namespace):
    # Store
    vector_memory_store(test_namespace, "apple", metadata="test1")
    
    # Verify file exists
    db_path = os.path.join(VECTOR_DIR, f"{test_namespace}.json")
    assert os.path.exists(db_path)
    
    # Create new instance to test loading
    db2 = VectorDB(test_namespace)
    assert len(db2.records) == 1
    assert db2.records[0]["text"] == "apple"
