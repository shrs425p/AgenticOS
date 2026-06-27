from typing import Optional, List

class ErrorCode:
    SECURITY_VIOLATION = "SECURITY_VIOLATION"
    PATH_TRAVERSAL = "PATH_TRAVERSAL"
    REGISTRY_TAMPERING = "REGISTRY_TAMPERING"
    COMMAND_BLOCKED = "COMMAND_BLOCKED"
    TOOL_EXECUTION_FAILED = "TOOL_EXECUTION_FAILED"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    TIMEOUT = "TIMEOUT"
    RATE_LIMIT_EXHAUSTED = "RATE_LIMIT_EXHAUSTED"
    SYSTEM_CRASH = "SYSTEM_CRASH"


class AgentError(Exception):
    """Unified exception class for all AgenticOS runtime errors."""
    def __init__(
        self,
        code: str,
        message: str,
        recovery_feasible: bool = False,
        suggestions: Optional[List[str]] = None,
        original_exception: Optional[Exception] = None
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.recovery_feasible = recovery_feasible
        self.suggestions = suggestions or []
        self.original_exception = original_exception

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "message": self.message,
            "recovery_feasible": self.recovery_feasible,
            "suggestions": self.suggestions,
            "original_exception": str(self.original_exception) if self.original_exception else None
        }

    def __str__(self) -> str:
        res = f"AgentError [{self.code}]: {self.message}"
        if self.suggestions:
            res += "\nSuggestions: " + "; ".join(self.suggestions)
        return res


class RateLimitExhausted(Exception):
    """Raised when a model provider rate limit is exhausted after all retries."""
    pass
