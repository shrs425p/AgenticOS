"""Tests for SemanticToolIndex in kernel/discovery.py."""

import pytest
from kernel.discovery import SemanticToolIndex


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_registry():
    """Return a mock tool registry with 5 ops."""
    return {
        "read_file": {
            "fn": lambda path: "",
            "desc": "Read the contents of a file from disk.",
            "category": "Files",
        },
        "write_file": {
            "fn": lambda path, content: "",
            "desc": "Write content to a file on disk.",
            "category": "Files",
        },
        "runcommand": {
            "fn": lambda cmd: "",
            "desc": "Execute a shell command in the terminal.",
            "category": "Terminal",
        },
        "websearch": {
            "fn": lambda query: "",
            "desc": "Search the web for information using a query string.",
            "category": "Web",
        },
        "memorysearch": {
            "fn": lambda query: "",
            "desc": "Search conversation memory for a substring.",
            "category": "Core",
        },
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSemanticToolIndex:
    """Tests for SemanticToolIndex."""

    def test_build_index(self):
        """Build index from 5 mock ops; verify internal index is populated."""
        index = SemanticToolIndex()
        registry = _make_registry()
        index.build(registry)

        assert index._built is True
        assert len(index._index) == 5
        assert len(index._idf) > 0
        # All tool names should be present in the index
        for name in registry:
            assert name in index._index

    def test_search_returns_relevant(self):
        """Search for 'file reading'; verify read_file is in top results."""
        index = SemanticToolIndex()
        index.build(_make_registry())

        results = index.search("file reading", top_k=10)
        assert len(results) > 0

        tool_names = [r[0] for r in results]
        assert "read_file" in tool_names, (
            f"Expected 'read_file' in results but got: {tool_names}"
        )

    def test_search_top_k(self):
        """Search with top_k=2 returns at most 2 results."""
        index = SemanticToolIndex()
        index.build(_make_registry())

        results = index.search("any tool query", top_k=2)
        assert len(results) <= 2

    def test_search_empty_query(self):
        """Empty query returns empty list."""
        index = SemanticToolIndex()
        index.build(_make_registry())

        assert index.search("") == []
        assert index.search("   ") == []

    def test_format_results(self):
        """format_results produces a readable, non-empty string for valid results."""
        index = SemanticToolIndex()
        index.build(_make_registry())

        results = index.search("file", top_k=3)
        formatted = index.format_results(results)

        assert isinstance(formatted, str)
        assert len(formatted) > 0
        # Should contain tool names
        for tool_name, skernel, desc in results:
            assert tool_name in formatted

    def test_format_results_empty(self):
        """format_results on an empty list returns a sensible placeholder string."""
        index = SemanticToolIndex()
        formatted = index.format_results([])
        assert "no" in formatted.lower() or "(" in formatted

    def test_rebuild_updates_index(self):
        """Build once, rebuild with a different registry; old ops should be gone."""
        index = SemanticToolIndex()
        index.build(_make_registry())

        # Confirm original ops present
        assert "read_file" in index._index

        # Rebuild with a completely different registry
        new_registry = {
            "send_email": {
                "fn": lambda to, body: "",
                "desc": "Send an email to a recipient.",
                "category": "Communication",
            },
            "make_call": {
                "fn": lambda number: "",
                "desc": "Initiate a phone call to a number.",
                "category": "Communication",
            },
        }
        index.build(new_registry)

        assert index._built is True
        assert "read_file" not in index._index, "Old tool should have been removed after rebuild"
        assert "send_email" in index._index
        assert "make_call" in index._index

    def test_search_before_build(self):
        """Searching before build() returns empty list gracefully."""
        index = SemanticToolIndex()
        results = index.search("anything")
        assert results == []

    def test_search_skernels_are_positive(self):
        """All returned skernels should be strictly positive."""
        index = SemanticToolIndex()
        index.build(_make_registry())

        results = index.search("shell terminal command", top_k=5)
        for _, skernel, _ in results:
            assert skernel > 0.0

    def test_search_results_sorted_descending(self):
        """Results should be sorted by descending skernel."""
        index = SemanticToolIndex()
        index.build(_make_registry())

        results = index.search("file disk read write", top_k=10)
        skernels = [r[1] for r in results]
        assert skernels == sorted(skernels, reverse=True), (
            "Results are not sorted by descending skernel"
        )
