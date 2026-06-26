from dataclasses import dataclass
from typing import Optional

@dataclass
class StallWarning:
    category: str
    threshold: float
    elapsed: float
    suggestion: str

class StallMonitor:
    """Monitors tool execution times and suggests faster alternatives if a timeout threshold is exceeded."""
    
    THRESHOLDS = {
        "file operations": 30.0,
        "network": 60.0,
        "package install": 300.0,
        "general": 120.0
    }
    
    SUGGESTIONS = {
        "file operations": "Consider using 'rg' (ripgrep) instead of standard grep, or using structured/bulk file tools for large directories.",
        "network": "If full page fetches are slow, prefer simple http fetches or API endpoints instead of browser automation.",
        "package install": "Use lock files, offline modes, or local cache directories to skip registry network checks.",
        "general": "Ensure background processes are not consuming resources, or split the task into smaller sub-tasks."
    }

    def get_category(self, tool_name: str) -> str:
        """Map a tool name to its performance category."""
        name = (tool_name or "").lower()
        if any(kw in name for kw in ["file", "dir", "grep", "search_file", "find", "archive", "stat", "listing"]):
            return "file operations"
        elif any(kw in name for kw in ["web", "fetch", "search_web", "url", "download", "http", "api"]):
            return "network"
        elif any(kw in name for kw in ["install", "pip", "npm", "package", "setup"]):
            return "package install"
        else:
            return "general"

    def check_stall(self, tool_name: str, elapsed_seconds: float) -> Optional[StallWarning]:
        """Check if execution time has exceeded the threshold for the tool's category."""
        category = self.get_category(tool_name)
        threshold = self.THRESHOLDS.get(category, 120.0)
        
        if elapsed_seconds > threshold:
            suggestion = self.SUGGESTIONS.get(category, "Check resource utilization.")
            return StallWarning(
                category=category,
                threshold=threshold,
                elapsed=elapsed_seconds,
                suggestion=suggestion
            )
        return None
