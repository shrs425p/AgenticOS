"""Semantic Vector Memory Plugin using numpy and OpenAI embeddings."""

from __future__ import annotations

import os
import json
import logging
from typing import Any, Dict, List

from core.tool_registry import tool
from openai import OpenAI

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
        self.records: List[Dict[str, Any]] = self._load()

    def _load(self) -> List[Dict[str, Any]]:
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logging.error(f"Failed to load vector DB {self.db_path}: {e}")
        return []

    def _save(self) -> None:
        try:
            with open(self.db_path, "w", encoding="utf-8") as f:
                json.dump(self.records, f, indent=2)
        except Exception as e:
            logging.error(f"Failed to save vector DB {self.db_path}: {e}")

    def get_embedding(self, text: str) -> List[float]:
        """Fetch embedding from OpenAI."""
        if not self.client:
            self.client = OpenAI()
        response = self.client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding

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
        """Search using cosine similarity."""
        if not self.records:
            return f"No records found in namespace '{self.namespace}'."
            
        try:
            query_vec = np.array(self.get_embedding(query))
            
            results = []
            for record in self.records:
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
