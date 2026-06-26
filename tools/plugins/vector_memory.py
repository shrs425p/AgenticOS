"""Semantic Vector Memory Plugin using numpy and OpenAI embeddings."""

from __future__ import annotations

import os
import json
import logging
from typing import Any, Dict, List

from core.tool_registry import tool

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

VECTOR_DIR = os.path.join("workspace", "vectors")
os.makedirs(VECTOR_DIR, exist_ok=True)


class VectorDB:
    """Lightweight Numpy-based Vector Database."""
    
    def __init__(self, namespace: str):
        self.namespace = namespace
        self.db_path = os.path.join(VECTOR_DIR, f"{namespace}.json")
        self.client = None # Lazily instantiated
        self.centroids = None
        self.records: List[Dict[str, Any]] = self._load()

    def _load(self) -> List[Dict[str, Any]]:
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict) and "records" in data:
                        self.centroids = data.get("centroids")
                        return data["records"]
                    else:
                        self.centroids = None
                        return data
            except Exception as e:
                logging.error(f"Failed to load vector DB {self.db_path}: {e}")
        return []

    def _save(self) -> None:
        try:
            with open(self.db_path, "w", encoding="utf-8") as f:
                data = {
                    "records": self.records,
                    "centroids": self.centroids
                }
                json.dump(data, f, indent=2)
        except Exception as e:
            logging.error(f"Failed to save vector DB {self.db_path}: {e}")

    def train_ivf(self, k: int = None) -> None:
        """Train IVF centroids using K-Means on the stored records' vectors."""
        if not HAS_NUMPY:
            return
        if len(self.records) <= 10:
            self.centroids = None
            self._save()
            return
        
        # Extract vectors
        vectors = np.array([r["vector"] for r in self.records], dtype=float) # Shape (N, D)
        N, D = vectors.shape
        
        if k is None:
            k = int(np.sqrt(N))
        if k < 2:
            k = 2
        if k > N:
            k = N
            
        # Standard K-Means implementation
        # Initialize centroids randomly from existing vectors to avoid empty clusters
        rng = np.random.default_rng(42)  # Seed for reproducibility in tests
        indices = rng.choice(N, size=k, replace=False)
        centroids = vectors[indices].copy()
        
        for _ in range(100):
            # Compute cosine similarity for assignment
            vec_norms = np.linalg.norm(vectors, axis=1, keepdims=True)
            vec_norms[vec_norms == 0] = 1e-9
            norm_vectors = vectors / vec_norms
            
            cent_norms = np.linalg.norm(centroids, axis=1, keepdims=True)
            cent_norms[cent_norms == 0] = 1e-9
            norm_centroids = centroids / cent_norms
            
            similarities = np.dot(norm_vectors, norm_centroids.T)
            assignments = np.argmax(similarities, axis=1)
            
            new_centroids = np.zeros_like(centroids)
            for i in range(k):
                mask = (assignments == i)
                if np.any(mask):
                    new_centroids[i] = np.mean(vectors[mask], axis=0)
                else:
                    rand_idx = rng.choice(N)
                    new_centroids[i] = vectors[rand_idx]
            
            if np.allclose(centroids, new_centroids, atol=1e-5):
                centroids = new_centroids
                break
            centroids = new_centroids
            
        self.centroids = centroids.tolist()
        self._save()

    def get_embedding(self, text: str) -> List[float]:
        """Fetch embedding from configured provider or fall back to local semantic mock."""
        # 1. Try OpenAI if API key exists
        openai_key = os.environ.get("OPENAI_API_KEY")
        if openai_key:
            try:
                from openai import OpenAI
                if not self.client or not hasattr(self.client, "_is_openai"):
                    self.client = OpenAI(api_key=openai_key)
                    self.client._is_openai = True
                response = self.client.embeddings.create(
                    model="text-embedding-3-small",
                    input=text
                )
                return response.data[0].embedding
            except Exception as e:
                logging.warning(f"OpenAI embedding retrieval failed: {e}")

        # 2. Try Nvidia NIM if API key exists
        nvidia_key = os.environ.get("NVIDIA_API_KEY")
        if nvidia_key:
            try:
                from openai import OpenAI
                base_url = "https://integrate.api.nvidia.com/v1"
                try:
                    from core.runtime_config import load_config
                    cfg = load_config()
                    base_url = cfg.get("cloud", {}).get("nvidia", {}).get("base_url", base_url)
                except Exception:
                    pass
                if not self.client or not hasattr(self.client, "_is_nvidia"):
                    self.client = OpenAI(base_url=base_url, api_key=nvidia_key)
                    self.client._is_nvidia = True
                response = self.client.embeddings.create(
                    model="nvidia/embeddings-nv-embed-qa-4",
                    input=text
                )
                return response.data[0].embedding
            except Exception as e:
                logging.warning(f"Nvidia embedding retrieval failed: {e}")

        # 3. Try Gemini if API key exists
        gemini_key = os.environ.get("GEMINI_API_KEY")
        if gemini_key:
            try:
                import requests
                url = f"https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent?key={gemini_key}"
                headers = {"Content-Type": "application/json"}
                payload = {"content": {"parts": [{"text": text}]}}
                response = requests.post(url, json=payload, headers=headers, timeout=10.0)
                if response.status_code == 200:
                    return response.json()["embedding"]["values"]
                else:
                    logging.warning(
                        "Gemini embedding API request failed with status %s",
                        response.status_code,
                    )
            except Exception as e:
                logging.warning(f"Gemini embedding retrieval failed: {e}")

        # 4. Deterministic Local Math Fallback (1536-dimensional unit vector)
        # Highly robust offline mathematical mock.
        try:
            import numpy as np
            h = 0
            for char in text:
                h = (h * 31 + ord(char)) & 0xFFFFFFFF
            rng = np.random.default_rng(h)
            vector = rng.standard_normal(1536)
            norm = np.linalg.norm(vector)
            if norm > 0:
                vector = vector / norm
            return vector.tolist()
        except Exception as e:
            logging.error(f"Fallback local embedding generation failed: {e}")
            return [0.0] * 1536

    def store(self, text: str, metadata: str) -> str:
        """Embed and store a record."""
        try:
            vec = self.get_embedding(text)
            self.records.append({
                "text": text,
                "metadata": metadata,
                "vector": vec
            })
            self._save()
            return f"Successfully stored vector for '{text[:30]}...' in namespace '{self.namespace}'"
        except Exception as e:
            return f"Error storing vector: {e}"

    def search(self, query: str, top_k: int = 5) -> str:
        """Search using cosine similarity with IVF partitioning if available."""
        if not self.records:
            return f"No records found in namespace '{self.namespace}'."
            
        try:
            query_vec = np.array(self.get_embedding(query))
            
            # IVF routing if centroids are present and database has > 10 records
            records_to_search = self.records
            if self.centroids and len(self.records) > 10:
                centroids_arr = np.array(self.centroids, dtype=float)
                # Compute similarities of query vector to centroids
                query_norm = np.linalg.norm(query_vec)
                query_norm = query_norm if query_norm > 0 else 1.0
                norm_query_vec = query_vec / query_norm
                
                cent_norms = np.linalg.norm(centroids_arr, axis=1)
                cent_norms[cent_norms == 0] = 1.0
                norm_centroids = centroids_arr / cent_norms[:, np.newaxis]
                
                centroid_sims = np.dot(norm_centroids, norm_query_vec)
                best_centroid_idx = int(np.argmax(centroid_sims))
                
                # Assign all records to their nearest centroid
                records_to_search = []
                rec_vectors = np.array([r["vector"] for r in self.records], dtype=float)
                rec_norms = np.linalg.norm(rec_vectors, axis=1)
                rec_norms[rec_norms == 0] = 1.0
                norm_rec_vectors = rec_vectors / rec_norms[:, np.newaxis]
                
                rec_to_cent_sims = np.dot(norm_rec_vectors, norm_centroids.T)
                rec_assignments = np.argmax(rec_to_cent_sims, axis=1)
                
                for idx, record in enumerate(self.records):
                    if rec_assignments[idx] == best_centroid_idx:
                        records_to_search.append(record)
                
                if not records_to_search:
                    records_to_search = self.records
            
            results = []
            for record in records_to_search:
                doc_vec = np.array(record["vector"])
                
                # Cosine similarity
                dot_product = np.dot(query_vec, doc_vec)
                norm_q = np.linalg.norm(query_vec)
                norm_d = np.linalg.norm(doc_vec)
                
                similarity = float(dot_product / (norm_q * norm_d)) if norm_q and norm_d else 0.0
                
                results.append({
                    "text": record["text"],
                    "metadata": record["metadata"],
                    "similarity": round(similarity, 4)
                })
                
            # Sort by similarity descending
            results.sort(key=lambda x: x["similarity"], reverse=True)
            top_results = results[:top_k]
            
            return json.dumps(top_results, indent=2)
            
        except Exception as e:
            return f"Error searching vectors: {e}"


@tool(name="vector_memory_store", category="Memory", desc="Store a semantically embedded memory.")
def vector_memory_store(namespace: str, text: str, metadata: str = "") -> str:
    """Store text as a semantic vector embedding.
    
    Args:
        namespace: The logical grouping/database name (e.g. 'code_snippets', 'user_facts').
        text: The string to embed and remember.
        metadata: Optional string context or JSON metadata about the memory.
    """
    if not HAS_NUMPY:
        return "Error: numpy is not installed. Please add numpy to requirements."
        
    db = VectorDB(namespace)
    return db.store(text, metadata)


@tool(name="vector_memory_search", category="Memory", desc="Semantically search memories.")
def vector_memory_search(namespace: str, query: str, top_k: int = 3) -> str:
    """Search for semantically relevant memories in a namespace.
    
    Args:
        namespace: The logical grouping to search within.
        query: The search query string.
        top_k: Number of results to return.
    """
    if not HAS_NUMPY:
        return "Error: numpy is not installed. Please add numpy to requirements."
        
    db = VectorDB(namespace)
    return db.search(query, top_k)
