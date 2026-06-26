import asyncio
import pytest
from typing import AsyncIterator, Any
from kernel.base import tool, AsyncTool
from kernel.dispatch import ParallelScheduler, pipe_ops
from kernel.registry import ToolRegistry

@tool(name="asyncdummytool")
async def dummy_async_tool(val: str) -> str:
    """A dummy async tool."""
    await asyncio.sleep(0.01)
    return f"processed_{val}"


def test_decorator_detects_async():
    """Verify that the @tool decorator correctly flags async functions."""
    assert getattr(dummy_async_tool, "_is_async", False) is True


def test_tool_registry_async_call():
    """Verify ToolRegistry.call returns a coroutine for async ops and returns correct value when run."""
    cfg = {"agent": {"workspace": "."}}
    registry = ToolRegistry(cfg)
    
    # Manually register the dummy async tool
    registry.registry["asyncdummytool"] = {
        "fn": dummy_async_tool,
        "desc": "dummy async tool",
        "category": "Core"
    }
    
    # Calling registry.call should return a coroutine
    res = registry.call("asyncdummytool", {"val": "hello"})
    assert asyncio.iscoroutine(res)
    
    # Run the coroutine
    val = asyncio.run(res)
    assert val == "processed_hello"


def test_parallel_scheduler_async_concurrent():
    """Verify that ParallelScheduler runs async ops concurrently in a wave."""
    async def run_delay_1(*args):
        await asyncio.sleep(0.1)
        return "done1"

    async def run_delay_2(*args):
        await asyncio.sleep(0.1)
        return "done2"

    def executor_fn(tool, args):
        if tool == "async_delay_1":
            return run_delay_1()
        elif tool == "async_delay_2":
            return run_delay_2()
        return "unknown"

    scheduler = ParallelScheduler(max_workers=2)
    actions = [
        {"tool": "async_delay_1", "args": {}},
        {"tool": "async_delay_2", "args": {}},
    ]
    
    # Use time.perf_counter to measure elapsed duration
    import time
    start_time = time.perf_counter()
    results = scheduler.execute(actions, executor_fn)
    end_time = time.perf_counter()
    
    assert results == ["done1", "done2"]
    # If run concurrently, total time is around 0.1s. If sequential, >= 0.2s.
    assert (end_time - start_time) < 0.18


@pytest.mark.anyio
async def test_pipe_ops_execution():
    """Verify that pipe_ops chains two ops correctly and processes stream outputs."""
    class ToolA:
        def __init__(self):
            self._is_tool = True
            self._is_async = True

        async def stream(self, val: str) -> AsyncIterator[str]:
            yield f"a_stream1_{val}"
            yield f"a_stream2_{val}"

    @tool(name="toolb")
    async def toolb(val: str) -> str:
        return f"b_{val}"

    tool_a = ToolA()
    piped = pipe_ops(tool_a, toolb)

    # Test calling piped
    res = await piped("test")
    assert res == "b_a_stream1_testa_stream2_test"

    # Test streaming piped
    stream_results = []
    async for chunk in piped.stream("test"):
        stream_results.append(chunk)
    
    assert stream_results == ["b_a_stream1_testa_stream2_test"]


@pytest.mark.anyio
async def test_pipe_ops_double_stream():
    """Verify that pipe_ops streams from toolb if both support streaming."""
    class ToolA:
        def __init__(self):
            self._is_tool = True
            self._is_async = True

        async def stream(self, val: str) -> AsyncIterator[str]:
            yield f"a_{val}"

    class ToolB:
        def __init__(self):
            self._is_tool = True
            self._is_async = True

        async def stream(self, val: str) -> AsyncIterator[str]:
            yield f"b1_{val}"
            yield f"b2_{val}"

    tool_a = ToolA()
    toolb = ToolB()
    piped = pipe_ops(tool_a, toolb)

    # Streaming piped should yield chunks from toolb
    stream_results = []
    async for chunk in piped.stream("test"):
        stream_results.append(chunk)

    assert stream_results == ["b1_a_test", "b2_a_test"]
