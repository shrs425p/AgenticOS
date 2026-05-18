"""Semantic / vector memory for AgenticOs.

Stores task summaries as embedding vectors so that the ContextEngine can
retrieve the *k* most relevant past memories for the current task using
cosine similarity, rather than injecting the entire flat MEMORY.md file.

Storage back-ends (in priority order):
1. ChromaDB (``chromadb`` package) — persistent, HNSW index, fast top-k.
2. Pure-Python in-process store — uses ``core.embeddings.TfidfEmbedder`` for
   cosine similarity; no extra dependencies.

The backend is selected at initialisation time and is transparent to callers.

Usage::

    vm = VectorMemory(workspace="workspace", cfg=cfg)
    vm.upsert("task-001", "The agent fetched stock prices and wrote a report.")
    results = vm.query("financial data analysis", k=3)
    # [{"id": "task-001", "text": "The agent ...", "score": 0.87}, ...]
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.embeddings import EmbeddingAdapter, TfidfEmbedder

logger = logging.getLogger(__name__)

_STORE_FILE = "vector_store.json"


class _InProcessStore:
    """Minimal in-process cosine-similarity store (no external deps)."""

    def __init__(self, store_path: Path):
        self.path = store_path
        self._docs: Dict[str, Dict[str, Any]] = {}
        self._tfidf = TfidfEmbedder()
        self._load()

    def _load(self):
        if self.path.exists():
            try:
                with open(self.path, "r", encoding="utf-8") as fh:
                    self._docs = json.load(fh)
            except Exception as exc:
                logger.warning("VectorMemory: failed to load store: %s", exc)

    def _save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as fh:
                json.dump(self._docs, fh, ensure_ascii=False, indent=2)
        except Exception as exc:
            logger.error("VectorMemory: failed to save store: %s", exc)

    def upsert(self, doc_id: str, text: str, embedding: List[float]):
        self._docs[doc_id] = {"text": text, "embedding": embedding}
        self._save()

    def query(self, embedding: List[float], k: int) -> List[Dict[str, Any]]:
        scores = []
        for doc_id, doc in self._docs.items():
            score = TfidfEmbedder.cosine(embedding, doc["embedding"])
            scores.append((score, doc_id, doc["text"]))
        scores.sort(reverse=True)
        return [
            {"id": did, "text": txt, "score": round(sc, 4)}
            for sc, did, txt in scores[:k]
        ]

    def count(self) -> int:
        return len(self._docs)


class VectorMemory:
    """High-level semantic memory interface.

    Args:
        workspace: Path to the agent workspace directory.
        cfg: Agent configuration dict.
    """

    def __init__(self, workspace: str, cfg: Optional[Dict] = None):
        self.cfg = cfg or {}
        memory_cfg = self.cfg.get("memory", {}) or {}
        self.enabled = bool(memory_cfg.get("vector_enabled", False))

        data_dir = Path(workspace).resolve().parent / "data" / "vector_memory"
        data_dir.mkdir(parents=True, exist_ok=True)
        self._data_dir = data_dir

        self._embedder = EmbeddingAdapter(cfg=self.cfg)
        self._backend_name = "none"
        self._chroma = None
        self._store: Optional[_InProcessStore] = None

        if self.enabled:
            self._init_backend()

    def _init_backend(self):
        try:
            import chromadb  # type: ignore

            self._chroma = chromadb.PersistentClient(path=str(self._data_dir))
            self._collection = self._chroma.get_or_create_collection("agenticos_memory")
            self._backend_name = "chromadb"
            logger.info("VectorMemory: using ChromaDB backend")
        except ImportError:
            store_path = self._data_dir / _STORE_FILE
            self._store = _InProcessStore(store_path)
            self._backend_name = "inprocess"
            logger.info("VectorMemory: ChromaDB not available; using in-process store")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def upsert(self, doc_id: str, text: str):
        """Add or update a document by ID.

        Args:
            doc_id: Unique identifier (e.g. task ID).
            text: Human-readable text to embed and store.
        """
        if not self.enabled or not text:
            return
        try:
            embedding = self._embedder.embed(text)
            if self._backend_name == "chromadb":
                self._collection.upsert(
                    ids=[doc_id],
                    embeddings=[embedding],
                    documents=[text],
                )
            elif self._store:
                self._store.upsert(doc_id, text, embedding)
        except Exception as exc:
            logger.error("VectorMemory.upsert failed: %s", exc)

    def query(self, text: str, k: int = 5) -> List[Dict[str, Any]]:
        """Retrieve the *k* most semantically similar stored documents.

        Args:
            text: Query string.
            k: Maximum number of results to return.

        Returns:
            List of dicts: ``[{"id": ..., "text": ..., "score": ...}, ...]``
        """
        if not self.enabled or not text:
            return []
        try:
            embedding = self._embedder.embed(text)
            if self._backend_name == "chromadb":
                results = self._collection.query(
                    query_embeddings=[embedding],
                    n_results=min(k, max(1, self._collection.count())),
                )
                ids = results.get("ids", [[]])[0]
                docs = results.get("documents", [[]])[0]
                dists = results.get("distances", [[]])[0]
                return [
                    {"id": i, "text": d, "score": round(1.0 - dist, 4)}
                    for i, d, dist in zip(ids, docs, dists)
                ]
            elif self._store:
                return self._store.query(embedding, k)
        except Exception as exc:
            logger.error("VectorMemory.query failed: %s", exc)
        return []

    def count(self) -> int:
        """Return the number of stored documents."""
        if not self.enabled:
            return 0
        try:
            if self._backend_name == "chromadb":
                return self._collection.count()
            elif self._store:
                return self._store.count()
        except Exception:
            pass
        return 0

    @property
    def backend(self) -> str:
        """Active storage backend name."""
        return self._backend_name
