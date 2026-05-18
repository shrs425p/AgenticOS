"""Embedding adapter for AgenticOs vector memory.

Supports three backends in priority order:
1. Ollama ``/api/embeddings`` endpoint (local, no extra deps)
2. OpenAI ``text-embedding-3-small`` (cloud, requires openai)
3. Pure-Python TF-IDF fallback (no external deps, lower quality)

The backend is selected automatically based on config and available libraries.
"""

from __future__ import annotations

import logging
import math
import os
import re
from collections import Counter
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# TF-IDF fallback
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> List[str]:
    return re.findall(r"\b[a-z]{2,}\b", text.lower())


class TfidfEmbedder:
    """Minimal TF-IDF vectorizer that produces sparse-style float lists.

    Maintains an in-memory vocabulary built from all texts seen so far.
    Dimensionality grows with vocabulary but is capped at 512.
    """

    _MAX_DIM = 512

    def __init__(self):
        self._vocab: Dict[str, int] = {}
        self._df: Counter = Counter()
        self._doc_count: int = 0

    def _ensure_vocab(self, tokens: List[str]):
        for tok in tokens:
            if tok not in self._vocab and len(self._vocab) < self._MAX_DIM:
                self._vocab[tok] = len(self._vocab)

    def embed(self, text: str) -> List[float]:
        tokens = _tokenize(text)
        self._ensure_vocab(tokens)
        self._doc_count += 1
        for tok in set(tokens):
            self._df[tok] += 1

        tf = Counter(tokens)
        total = max(1, len(tokens))
        dim = min(len(self._vocab), self._MAX_DIM)
        vec = [0.0] * dim
        for tok, count in tf.items():
            idx = self._vocab.get(tok)
            if idx is None or idx >= dim:
                continue
            tf_val = count / total
            df = self._df.get(tok, 1)
            idf = math.log((self._doc_count + 1) / (df + 1)) + 1.0
            vec[idx] = tf_val * idf

        # L2-normalise
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]

    @staticmethod
    def cosine(a: List[float], b: List[float]) -> float:
        """Cosine similarity between two vectors (handles different lengths)."""
        min_len = min(len(a), len(b))
        if min_len == 0:
            return 0.0
        dot = sum(a[i] * b[i] for i in range(min_len))
        na = math.sqrt(sum(x * x for x in a)) or 1.0
        nb = math.sqrt(sum(x * x for x in b)) or 1.0
        return dot / (na * nb)


# ---------------------------------------------------------------------------
# Public adapter
# ---------------------------------------------------------------------------

class EmbeddingAdapter:
    """Unified embedding interface.

    Selects backend automatically:
    - ``ollama``  → Ollama /api/embeddings
    - ``openai``  → OpenAI text-embedding-3-small
    - ``tfidf``   → built-in TF-IDF fallback
    """

    def __init__(self, cfg: Optional[Dict] = None):
        self.cfg = cfg or {}
        memory_cfg = self.cfg.get("memory", {}) or {}
        self.backend = memory_cfg.get("embedding_backend", "auto").lower()
        self._tfidf = TfidfEmbedder()
        self._selected: Optional[str] = None

        if self.backend == "auto":
            self._selected = self._detect_backend()
        elif self.backend in ("ollama", "openai", "tfidf"):
            self._selected = self.backend
        else:
            logger.warning(
                "Unknown embedding_backend '%s'; falling back to tfidf", self.backend
            )
            self._selected = "tfidf"

    def _detect_backend(self) -> str:
        # Prefer Ollama if base_url is configured
        ollama_url = (
            self.cfg.get("ollama", {}).get("base_url")
            or "http://localhost:11434"
        )
        try:
            import requests

            r = requests.get(f"{ollama_url}/api/tags", timeout=2)
            if r.status_code == 200:
                return "ollama"
        except Exception:
            pass

        # OpenAI if key available
        if os.environ.get("OPENAI_API_KEY"):
            try:
                import openai  # noqa: F401

                return "openai"
            except ImportError:
                pass

        return "tfidf"

    def embed(self, text: str) -> List[float]:
        """Return an embedding vector for *text*."""
        backend = self._selected or "tfidf"
        try:
            if backend == "ollama":
                return self._embed_ollama(text)
            if backend == "openai":
                return self._embed_openai(text)
        except Exception as exc:
            logger.warning(
                "Embedding backend '%s' failed (%s); falling back to tfidf", backend, exc
            )
        return self._tfidf.embed(text)

    def _embed_ollama(self, text: str) -> List[float]:
        import requests

        ollama_url = self.cfg.get("ollama", {}).get("base_url", "http://localhost:11434")
        embed_model = (
            self.cfg.get("memory", {}).get("embed_model")
            or self.cfg.get("ollama", {}).get("default_model", "nomic-embed-text")
        )
        resp = requests.post(
            f"{ollama_url}/api/embeddings",
            json={"model": embed_model, "prompt": text},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["embedding"]

    def _embed_openai(self, text: str) -> List[float]:
        from openai import OpenAI

        api_key = os.environ.get("OPENAI_API_KEY", "")
        client = OpenAI(api_key=api_key)
        resp = client.embeddings.create(
            input=text,
            model="text-embedding-3-small",
        )
        return resp.data[0].embedding

    @property
    def selected_backend(self) -> str:
        return self._selected or "tfidf"
