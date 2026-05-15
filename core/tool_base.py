"""Base classes and decorators for AgenticOs tools."""



def tool(
    name: str = None,
    desc: str = None,
    category: str = "general",
    version: str = "1.0.0",
    author: str = "AgenticOs",
):
    """Decorator to mark a function as a tool for AgenticOs."""

    def decorator(func):
        func._is_tool = True
        func._tool_name = name or func.__name__
        doc = func.__doc__ or "No description provided."
        func._tool_desc = desc or doc.strip().split("\n")[0]
        func._tool_category = category
        func._tool_version = version
        func._tool_author = author
        return func

    return decorator


def _size_human(n: int) -> str:
    """Convert bytes to a human-readable string."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"
