"""Tests for StreamingActionParser and ParallelScheduler in kernel/dispatch.py."""

import threading
import time
import pytest

from kernel.dispatch import (
    StreamingActionParser,
    ParallelScheduler,
    execute_actions_parallel,
)


# ---------------------------------------------------------------------------
# StreamingActionParser spec
# ---------------------------------------------------------------------------


class TestStreamingActionParser:
    """Tests for the StreamingActionParser class."""

    def test_streaming_parser_simple_json(self):
        """Feed a complete ACTION: JSON block all at once; verify result."""
        parser = StreamingActionParser()
        text = 'ACTION: {"tool": "runcommand", "args": {"cmd": "ls"}}'
        # Feed the complete text; since the buffer ends with }, it should extract immediately
        results = parser.feed(text)
        # If not extracted by feed, flush should get it
        if not results:
            results = parser.flush()
        assert len(results) == 1
        tool, args = results[0]
        assert tool == "runcommand"
        assert args == {"cmd": "ls"}

    def test_streaming_parser_chunked(self):
        """Feed the same ACTION in multiple small 5-char chunks; verify result."""
        parser = StreamingActionParser()
        text = 'ACTION: {"tool": "runcommand", "args": {"cmd": "ls"}}'
        # Feed 5 characters at a time
        collected = []
        for i in range(0, len(text), 5):
            chunk = text[i : i + 5]
            collected.extend(parser.feed(chunk))
        # Flush any remaining
        collected.extend(parser.flush())
        assert len(collected) == 1
        tool, args = collected[0]
        assert tool == "runcommand"
        assert args == {"cmd": "ls"}

    def test_streaming_parser_multiple_feeds(self):
        """Feed text with a keyword terminator; ACTION before it should be parsed."""
        parser = StreamingActionParser()
        # Feed the ACTION block followed by OBSERVATION: which acts as a terminator
        text = 'ACTION: {"tool": "read_file", "args": {"path": "/tmp/x.txt"}} OBSERVATION: file contents'
        results = parser.feed(text)
        assert len(results) == 1
        tool, args = results[0]
        assert tool == "read_file"
        assert args == {"path": "/tmp/x.txt"}

    def test_streaming_parser_flush(self):
        """Feed an incomplete (unterminated) action, then flush() should parse remainder."""
        parser = StreamingActionParser()
        text = 'ACTION: {"tool": "list_dir", "args": {"directory": "/tmp"}}'
        # Feed it — since it ends with }, the feed may or may not extract it.
        # Either way, flush() must return the parsed result.
        results = parser.feed(text)
        if not results:
            results = parser.flush()
        else:
            parser.flush()  # ensure no error on empty flush
        assert len(results) == 1
        tool, args = results[0]
        assert tool == "list_dir"
        assert args == {"directory": "/tmp"}

    def test_streaming_parser_reset(self):
        """Feed partial text, reset(), then feed a new action."""
        parser = StreamingActionParser()
        # Feed partial/garbage text
        parser.feed('ACTION: {"tool": "old_tool", "args": {')
        # Reset clears the buffer
        parser.reset()
        # Now feed a fresh valid action
        text = 'ACTION: {"tool": "new_tool", "args": {"key": "val"}}'
        results = parser.feed(text)
        if not results:
            results = parser.flush()
        assert len(results) == 1
        tool, args = results[0]
        assert tool == "new_tool"
        assert args == {"key": "val"}


# ---------------------------------------------------------------------------
# ParallelScheduler spec
# ---------------------------------------------------------------------------


class TestParallelScheduler:
    """Tests for ParallelScheduler and execute_actions_parallel."""

    def _make_executor(self, delay: float = 0.0):
        """Return a simple executor_fn that records call order."""
        call_log = []
        lock = threading.Lock()

        def executor_fn(tool: str, args: dict) -> str:
            if delay:
                time.sleep(delay)
            with lock:
                call_log.append(tool)
            return f"result_of_{tool}"

        return executor_fn, call_log

    def test_parallel_scheduler_no_deps(self):
        """Execute 3 independent actions concurrently; verify all 3 observations returned."""
        actions = [
            {"tool": "tool_a", "args": {}},
            {"tool": "toolb", "args": {}},
            {"tool": "tool_c", "args": {}},
        ]

        def executor_fn(tool, args):
            return f"done_{tool}"

        scheduler = ParallelScheduler(max_workers=3)
        results = scheduler.execute(actions, executor_fn)
        assert len(results) == 3
        assert results[0] == "done_tool_a"
        assert results[1] == "done_toolb"
        assert results[2] == "done_tool_c"

    def test_parallel_scheduler_with_deps(self):
        """Action B depends on action A (depends_on=[0]); verify A completes before B starts."""
        completion_order = []
        lock = threading.Lock()

        def executor_fn(tool, args):
            time.sleep(0.01)  # small delay to make race conditions visible
            with lock:
                completion_order.append(tool)
            return f"done_{tool}"

        actions = [
            {"tool": "tool_a", "args": {}},               # index 0 — no deps
            {"tool": "toolb", "args": {}, "depends_on": [0]},  # index 1 — depends on 0
        ]
        scheduler = ParallelScheduler(max_workers=4)
        results = scheduler.execute(actions, executor_fn)

        assert len(results) == 2
        assert results[0] == "done_tool_a"
        assert results[1] == "done_toolb"
        # tool_a must have completed before toolb started (Kahn's wave ordering)
        assert completion_order.index("tool_a") < completion_order.index("toolb")

    def test_parallel_scheduler_sequential_fallback(self):
        """When enabled=False, execute_actions_parallel uses sequential execution."""
        call_order = []

        def executor_fn(tool, args):
            call_order.append(tool)
            return f"seq_{tool}"

        actions = [("alpha", {}), ("beta", {}), ("gamma", {})]
        results = execute_actions_parallel(
            actions, executor_fn, max_workers=4, enabled=False
        )
        assert results == ["seq_alpha", "seq_beta", "seq_gamma"]
        assert call_order == ["alpha", "beta", "gamma"]

    def test_parallel_scheduler_single_action(self):
        """A single action always runs sequentially (no thread overhead)."""
        call_count = {"n": 0}

        def executor_fn(tool, args):
            call_count["n"] += 1
            return "single_result"

        results = execute_actions_parallel([("only_tool", {})], executor_fn)
        assert results == ["single_result"]
        assert call_count["n"] == 1

    def test_parallel_scheduler_exception_handling(self):
        """If one tool raises, the exception is captured; other results still returned."""

        def executor_fn(tool, args):
            if tool == "bad_tool":
                raise RuntimeError("tool exploded")
            return f"ok_{tool}"

        actions = [
            {"tool": "good_tool_1", "args": {}},
            {"tool": "bad_tool", "args": {}},
            {"tool": "good_tool_2", "args": {}},
        ]
        scheduler = ParallelScheduler(max_workers=3)
        results = scheduler.execute(actions, executor_fn)

        assert len(results) == 3
        assert results[0] == "ok_good_tool_1"
        assert results[2] == "ok_good_tool_2"
        # The bad tool result should be an error string, not a raised exception
        assert "bad_tool" in results[1]
        assert "RuntimeError" in results[1] or "exploded" in results[1]
