"""Parallel tool execution engine for AgenticOs.

Allows multiple independent tool calls to run concurrently using a thread pool,
dramatically speeding up batch-style tasks (e.g. fetch 10 URLs at once).
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ParallelExecutor:
    """Executes a batch of tool calls concurrently and returns ordered results.

    Usage::

        executor = ParallelExecutor(max_workers=4)
        jobs = [
            ("fetch_url", {"url": "https://example.com"}),
            ("fetch_url", {"url": "https://python.org"}),
        ]
        results = executor.run(dispatch_fn=registry.call, jobs=jobs)

    Each result entry is ``{"tool": name, "args": args, "result": ..., "error": ...}``.
    Failures are surfaced per-job and never abort the whole batch.
    """

    def __init__(self, max_workers: int = 4):
        self.max_workers = max(1, max_workers)

    def run(
        self,
        dispatch_fn: Callable[[str, Any], Any],
        jobs: List[Tuple[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Run *jobs* concurrently and return results in submission order.

        Args:
            dispatch_fn: A callable ``(tool_name, args) -> result`` (typically
                         ``ToolRegistry.call``).
            jobs: Ordered list of ``(tool_name, args)`` pairs.

        Returns:
            List of result dicts, one per job, in the original order::

                [
                    {"tool": "fetch_url", "args": {...}, "result": "...", "error": None},
                    {"tool": "fetch_url", "args": {...}, "result": None,  "error": "..."},
                ]
        """
        if not jobs:
            return []

        results: List[Optional[Dict[str, Any]]] = [None] * len(jobs)

        # Map Future → original index so we can preserve order.
        future_to_index: Dict[Future, int] = {}

        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            for idx, (tool_name, args) in enumerate(jobs):
                future = pool.submit(dispatch_fn, tool_name, args)
                future_to_index[future] = idx

            for future in as_completed(future_to_index):
                idx = future_to_index[future]
                tool_name, args = jobs[idx]
                try:
                    result = future.result()
                    results[idx] = {
                        "tool": tool_name,
                        "args": args,
                        "result": result,
                        "error": None,
                    }
                except Exception as exc:
                    logger.warning(
                        "Parallel tool '%s' failed: %s", tool_name, exc
                    )
                    results[idx] = {
                        "tool": tool_name,
                        "args": args,
                        "result": None,
                        "error": str(exc),
                    }

        return results  # type: ignore[return-value]

    def format_results(self, results: List[Dict[str, Any]]) -> str:
        """Format a batch result list as a human-readable observation string."""
        lines = []
        for i, item in enumerate(results, 1):
            tool = item.get("tool", "?")
            if item.get("error"):
                lines.append(f"[{i}] {tool} → ERROR: {item['error']}")
            else:
                res = str(item.get("result") or "")
                preview = res[:300] + ("…" if len(res) > 300 else "")
                lines.append(f"[{i}] {tool} → {preview}")
        return "\n".join(lines)
