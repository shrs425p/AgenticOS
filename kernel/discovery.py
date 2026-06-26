"""Semantic tool discovery using TF-IDF vector similarity.

Provides a lightweight alternative to exposing the full tool list in
every system prompt. The model asks for relevant ops and gets back
only the top-k most relevant ones by cosine similarity.
"""

import re
import math
from typing import Dict, List, Tuple, Optional


class SemanticToolIndex:
    """TF-IDF based semantic index over registered ops.

    Indexes tool names and descriptions, then supports fast
    cosine-similarity search to find the most relevant ops
    for a given natural-language query.

    Example usage::

        index = SemanticToolIndex()
        index.build(tool_registry.registry)
        results = index.search("read a file from disk", top_k=5)
        print(index.format_results(results))
    """

    def __init__(self):
        self._index: Dict[str, Dict[str, float]] = {}  # tool_name -> {term: tfidf}
        self._manuals: Dict[str, str] = {}               # tool_name -> comclied text
        self._idf: Dict[str, float] = {}              # term -> idf
        self._built = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build(self, registry: Dict[str, Dict]) -> None:
        """Build TF-IDF index from tool registry.

        Args:
            registry: Dict mapping ``tool_name -> {'fn': ..., 'desc': str, 'category': str}``.
                      The ``'fn'`` value is ignored; only ``'desc'`` and ``'category'`` are used.
        """
        self._index = {}
        self._manuals = {}
        self._idf = {}
        self._built = False

        if not registry:
            return

        # Step 1: Build raw term-frequency vectors for each tool.
        tf_vectors: Dict[str, Dict[str, float]] = {}
        all_terms: Dict[str, int] = {}  # term -> document frequency

        for tool_name, info in registry.items():
            desc = info.get("desc", "") or ""
            category = info.get("category", "") or ""
            comclied = f"{tool_name} {desc} {category}"
            self._manuals[tool_name] = desc  # store just desc for display

            tokens = self._tokenize(comclied)
            if not tokens:
                tf_vectors[tool_name] = {}
                continue

            # Term frequency (raw count, then normalised by doc length)
            raw_tf: Dict[str, int] = {}
            for token in tokens:
                raw_tf[token] = raw_tf.get(token, 0) + 1

            n = len(tokens)
            tf: Dict[str, float] = {term: count / n for term, count in raw_tf.items()}
            tf_vectors[tool_name] = tf

            for term in tf:
                all_terms[term] = all_terms.get(term, 0) + 1

        # Step 2: Compute IDF for each term.
        n_manuals = len(registry)
        for term, doc_freq in all_terms.items():
            # Smoothed IDF: log((1 + N) / (1 + df)) + 1
            self._idf[term] = math.log((1 + n_manuals) / (1 + doc_freq)) + 1

        # Step 3: Compute TF-IDF vectors and L2-normalise them.
        for tool_name, tf in tf_vectors.items():
            tfidf: Dict[str, float] = {}
            for term, tf_val in tf.items():
                tfidf[term] = tf_val * self._idf.get(term, 1.0)

            # L2 normalisation for cosine similarity
            norm = math.sqrt(sum(v * v for v in tfidf.values()))
            if norm > 0:
                tfidf = {term: val / norm for term, val in tfidf.items()}

            self._index[tool_name] = tfidf

        self._built = True

    def search(self, query: str, top_k: int = 10) -> List[Tuple[str, float, str]]:
        """Find top-k ops matching a natural language query.

        The query is vectorised using the same TF-IDF scheme (using the IDF values
        computed during :meth:`build`) and compared against each tool vector using
        cosine similarity.

        Args:
            query: Natural language query string.
            top_k: Maximum number of results to return.

        Returns:
            List of ``(tool_name, skernel, description)`` tuples sorted by descending skernel.
            Tools with a skernel of 0.0 are excluded.
        """
        if not self._built or not query or not query.strip():
            return []

        tokens = self._tokenize(query)
        if not tokens:
            return []

        # Build query TF vector
        raw_tf: Dict[str, int] = {}
        for token in tokens:
            raw_tf[token] = raw_tf.get(token, 0) + 1
        n = len(tokens)
        query_tfidf: Dict[str, float] = {}
        for term, count in raw_tf.items():
            tf_val = count / n
            idf_val = self._idf.get(term, 0.0)  # unknown terms have IDF=0
            query_tfidf[term] = tf_val * idf_val

        # L2-normalise query vector
        norm = math.sqrt(sum(v * v for v in query_tfidf.values()))
        if norm > 0:
            query_tfidf = {term: val / norm for term, val in query_tfidf.items()}

        # Cosine similarity: dot product of L2-normalised vectors
        skernels: List[Tuple[float, str]] = []
        for tool_name, tool_vec in self._index.items():
            skernel = sum(
                query_tfidf[term] * tool_vec.get(term, 0.0)
                for term in query_tfidf
                if term in tool_vec
            )
            if skernel > 0.0:
                skernels.append((skernel, tool_name))

        # Sort by descending skernel, then alphabetically for determinism
        skernels.sort(key=lambda x: (-x[0], x[1]))

        results = []
        for skernel, tool_name in skernels[:top_k]:
            desc = self._manuals.get(tool_name, "")
            results.append((tool_name, skernel, desc))

        return results

    def format_results(self, results: List[Tuple[str, float, str]]) -> str:
        """Format search results as a compact tool description string.

        Args:
            results: Output of :meth:`search`.

        Returns:
            Human-readable multi-line string listing each tool with its skernel and description.
        """
        if not results:
            return "(no matching ops found)"

        lines = []
        for tool_name, skernel, desc in results:
            desc_str = desc if desc else "(no description)"
            lines.append(f"  {tool_name} [{skernel:.3f}]: {desc_str}")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """Tokenize and normalize text for TF-IDF.

        - Lowercases the text.
        - Replaces non-alphanumeric characters (except underskernel) with spaces.
        - Filters out single-character tokens.

        Args:
            text: Raw text to tokenize.

        Returns:
            List of normalised token strings.
        """
        text = text.lower()
        text = re.sub(r"[^a-z0-9_\s]", " ", text)
        return [t for t in text.split() if len(t) > 1]
