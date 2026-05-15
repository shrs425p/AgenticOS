import sys
import os
from core.tool_base import tool

class SystemManager:
    """
    Manager for agent session and system lifecycle.
    """
    def __init__(self, rules: dict = None, cfg: dict = None):
        self.rules = rules or {}
        self.cfg = cfg or {}

    @tool(
        name="exit_agent",
        desc="Gracefully terminates the current agent session and exits the program.",
        category="System"
    )
    def exit_agent(self, reason: str = "User requested exit") -> str:
        """
        Exits the agent process.
        Args:
            reason: The reason for exiting.
        """
        print(f"\n[SYSTEM] Agent shutting down: {reason}")
        # We use os._exit to bypass any catch-all try blocks in the runtime loop
        os._exit(0)
        return "Shutting down..."

