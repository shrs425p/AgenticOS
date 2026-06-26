"""Unit spec for the vector memory plugin."""

import os
import json
import time
import pytest
from unittest.mock import patch

from ops.addons.vector import (
    vectormemorystore,
    vectormemorysearch,
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
def test_vectormemorystore_and_search(test_namespace):
    # Store test records
    res1 = vectormemorystore(test_namespace, "I like eating an apple", metadata="fruit")
    assert "Successfully stored" in res1
    
    vectormemorystore(test_namespace, "Driving a fast car", metadata="vehicle")
    vectormemorystore(test_namespace, "A large truck on the highway", metadata="vehicle")
    vectormemorystore(test_namespace, "Peeling a banana", metadata="fruit")
    
    # Search for fruit-related text
    search_res = vectormemorysearch(test_namespace, "apple", top_k=2)
    results = json.loads(search_res)
    
    assert len(results) == 2
    # The exact match should have highest similarity (1.0)
    assert "apple" in results[0]["text"].lower()
    # The related concept should be second (0.9)
    assert "banana" in results[1]["text"].lower()


@pytest.mark.skipif(not HAS_NUMPY, reason="numpy is not installed")
@patch.object(VectorDB, 'get_embedding', new=mock_get_embedding)
def test_vectormemorysearch_empty(test_namespace):
    res = vectormemorysearch(test_namespace, "apple")
    assert "No records found" in res


@pytest.mark.skipif(not HAS_NUMPY, reason="numpy is not installed")
@patch.object(VectorDB, 'get_embedding', new=mock_get_embedding)
def test_vector_memory_persistence(test_namespace):
    # Store
    vectormemorystore(test_namespace, "apple", metadata="test1")
    
    # Verify file exists
    db_path = os.path.join(VECTOR_DIR, f"{test_namespace}.json")
    assert os.path.exists(db_path)
    
    # Create new instance to test loading
    db2 = VectorDB(test_namespace)
    assert len(db2.records) == 1
    assert db2.records[0]["text"] == "apple"


@pytest.mark.skipif(not HAS_NUMPY, reason="numpy is not installed")
@patch.object(VectorDB, 'get_embedding', new=mock_get_embedding)
def test_ivf_partitioning(test_namespace):
    db = VectorDB(test_namespace)
    # Store 6 fruit memories
    for i in range(6):
        db.store(f"apple {i}", metadata="fruit")
    # Store 6 vehicle memories
    for i in range(6):
        db.store(f"car {i}", metadata="vehicle")
        
    assert len(db.records) == 12
    
    # Train IVF with K=2
    db.train_ivf(k=2)
    assert db.centroids is not None
    assert len(db.centroids) == 2
    
    # Search for apple. Since apple is a fruit, and we only search the nearest centroid partition,
    # we should only find fruit items and no vehicle items.
    res_str = db.search("apple", top_k=10)
    results = json.loads(res_str)
    
    # Check that we only got fruit results
    for r in results:
        assert "apple" in r["text"].lower() or "fruit" in r["metadata"]
        assert "car" not in r["text"].lower()


@pytest.mark.skipif(not HAS_NUMPY, reason="numpy is not installed")
@patch.object(VectorDB, 'get_embedding', new=mock_get_embedding)
def test_exponential_time_decay(test_namespace):
    db = VectorDB(test_namespace)
    now = time.time()
    
    # Store identical texts at different timestamps to verify decay
    db.store("apple pie", metadata="fresh", timestamp=now)
    db.store("apple pie", metadata="aged_30", timestamp=now - 30 * 86400)
    db.store("apple pie", metadata="aged_60", timestamp=now - 60 * 86400)
    
    res_str = db.search("apple", top_k=3)
    results = json.loads(res_str)
    
    assert len(results) == 3
    assert results[0]["metadata"] == "fresh"
    assert results[1]["metadata"] == "aged_30"
    assert results[2]["metadata"] == "aged_60"
    
    fresh_skernel = results[0]["similarity"]
    aged_30_skernel = results[1]["similarity"]
    aged_60_skernel = results[2]["similarity"]
    
    # Verify half-life of 30 days
    assert pytest.approx(aged_30_skernel, abs=0.05) == fresh_skernel * 0.5
    assert pytest.approx(aged_60_skernel, abs=0.05) == fresh_skernel * 0.25


@pytest.mark.skipif(not HAS_NUMPY, reason="numpy is not installed")
@patch.object(VectorDB, 'get_embedding', new=mock_get_embedding)
def test_evidence_filtering(test_namespace):
    db = VectorDB(test_namespace)
    
    db.store("apple 1", metadata=json.dumps({"source": "unverified"}))
    db.store("apple 2", metadata=json.dumps({"evidence": "Verified fact from paper X", "source": "verified"}))
    
    # Without evidence requirement, should return both
    res_all = json.loads(db.search("apple", top_k=5, evidence_required=False))
    assert len(res_all) == 2
    
    # With evidence required, should only return verified one
    res_filtered = json.loads(db.search("apple", top_k=5, evidence_required=True))
    assert len(res_filtered) == 1
    assert "apple 2" in res_filtered[0]["text"]


@pytest.mark.skipif(not HAS_NUMPY, reason="numpy is not installed")
@patch.object(VectorDB, 'get_embedding', new=mock_get_embedding)
def test_clustermemories_tool(test_namespace):
    from ops.addons.vector import clustermemories
    
    vectormemorystore(test_namespace, "I like eating an apple", metadata="fruit")
    vectormemorystore(test_namespace, "Peeling a banana", metadata="fruit")
    vectormemorystore(test_namespace, "Sweet red apples", metadata="fruit")
    
    vectormemorystore(test_namespace, "Driving a fast car", metadata="vehicle")
    vectormemorystore(test_namespace, "A large truck", metadata="vehicle")
    vectormemorystore(test_namespace, "Red sports cars", metadata="vehicle")
    
    clusters_str = clustermemories(test_namespace, k=2)
    clusters = json.loads(clusters_str)
    
    assert len(clusters) == 2
    for c in clusters:
        assert "cluster_id" in c
        assert "size" in c
        assert "representative_text" in c
        assert "representative_metadata" in c
        assert c["size"] == 3


@pytest.mark.skipif(not HAS_NUMPY, reason="numpy is not installed")
@patch.object(VectorDB, 'get_embedding', new=mock_get_embedding)
def test_cross_instance_sharing():
    shared_namespace = "shared_test"
    shared_dir = os.path.join("workspace", "vectors", "shared")
    db_path = os.path.join(shared_dir, f"{shared_namespace}.json")
    
    if os.path.exists(db_path):
        os.remove(db_path)
        
    try:
        vectormemorystore(shared_namespace, "shared apple memory", metadata="shared_fruit", shared=True)
        assert os.path.exists(db_path)
        
        db2 = VectorDB(shared_namespace, shared=True)
        assert len(db2.records) == 1
        assert db2.records[0]["text"] == "shared apple memory"
        assert db2.records[0]["metadata"] == "shared_fruit"
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)

