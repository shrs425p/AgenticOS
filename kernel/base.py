"""Base classes and decorators for AgenticOs ops."""

import asyncio
from typing import Protocol, Callable, Any, AsyncIterator
from pydantic import BaseModel, Field

class ToolMetadata(BaseModel):
    name: str = Field(..., description="The name of the tool")
    description: str = Field(..., description="A short description of what the tool does")
    category: str = Field("General", description="Tool category classification")
    version: str = Field("1.0.0", description="Version string")
    author: str = Field("AgenticOS", description="Author identifier")

class Tool(Protocol):
    metadata: ToolMetadata
    func: Callable
    
    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Execute the tool function directly."""
        ...

class AsyncTool(Protocol):
    metadata: ToolMetadata
    func: Callable
    
    async def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Execute the tool function directly as a coroutine."""
        ...

    async def stream(self, *args: Any, **kwargs: Any) -> AsyncIterator[str]:
        """Stream chunks of output as an async generator."""
        ...

def tool(
    name: str = None,
    desc: str = None,
    category: str = "general",
    version: str = "1.0.0",
    author: str = "AgenticOs",
):
    """Decorator to mark a function as a tool for AgenticOs."""

    def decorator(func):
        """decorator function."""
        func._is_tool = True
        func._tool_name = name or func.__name__
        doc = func.__doc__ or "No description provided."
        func._tool_desc = desc or doc.strip().split("\n")[0]
        func._tool_category = category
        func._tool_version = version
        func._tool_author = author
        func._is_async = asyncio.iscoroutinefunction(func)
        return func

    return decorator


def _size_human(n: int) -> str:
    """Convert bytes to a human-readable string."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"
