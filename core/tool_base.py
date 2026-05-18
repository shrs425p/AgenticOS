"""Base classes and decorators for AgenticOs tools."""

import logging
import warnings

logger = logging.getLogger(__name__)

# Required fields enforced on every @tool registration when strict mode is on.
_REQUIRED_FIELDS = ("desc", "category", "version")
_STRICT_VALIDATION = False  # Set to True via config to hard-fail on missing fields


def configure_tool_validation(strict: bool = False):
    """Configure whether tool schema validation raises errors or only warns.

    Args:
        strict: If True, missing required fields raise ValueError.
                If False (default), a warning is emitted instead.
    """
    global _STRICT_VALIDATION
    _STRICT_VALIDATION = bool(strict)


def validate_tool_schema(name: str, desc: str, category: str, version: str) -> list:
    """Validate that a tool has the required schema fields.

    Returns:
        List of validation error strings (empty list = valid).
    """
    errors = []
    if not name or not str(name).strip():
        errors.append("'name' must be a non-empty string")
    if not desc or str(desc).strip() in ("No description provided.", ""):
        errors.append("'desc' should provide a meaningful description")
    if not category or not str(category).strip():
        errors.append("'category' must be a non-empty string")
    if not version or not str(version).strip():
        errors.append("'version' must be a non-empty string")
    return errors


def tool(
    name: str = None,
    desc: str = None,
    category: str = "general",
    version: str = "1.0.0",
    author: str = "AgenticOs",
):
    """Decorator to mark a function as a tool for AgenticOs.

    Required fields (enforced via schema validation):
      - desc: A meaningful description of what the tool does.
      - category: Logical grouping (e.g. 'files', 'web', 'system').
      - version: Semantic version string (e.g. '1.0.0').
    """

    def decorator(func):
        tool_name = name or func.__name__
        doc = func.__doc__ or "No description provided."
        tool_desc = desc or doc.strip().split("\n")[0]

        errors = validate_tool_schema(
            name=tool_name,
            desc=tool_desc,
            category=category,
            version=version,
        )
        if errors:
            msg = f"Tool '{tool_name}' schema issues: {'; '.join(errors)}"
            if _STRICT_VALIDATION:
                raise ValueError(msg)
            else:
                logger.debug(msg)

        func._is_tool = True
        func._tool_name = tool_name
        func._tool_desc = tool_desc
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
