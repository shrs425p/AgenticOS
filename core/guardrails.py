
from pathlib import Path
from typing import Dict, List, Tuple, Callable, Optional
from core.logger import get_logger
logger = get_logger(__name__)




class PathGuard:
    def __init__(self, cfg: Dict, on_confirm: Optional[Callable[[str, str], bool]] = None):
        self.cfg = cfg
        self.on_confirm = on_confirm
        security = cfg.get("security", {})
        self.enabled: bool = security.get("enable_zone_guard", True)
        self.blocked_paths: List[Path] = [
            Path(p).resolve() for p in security.get("blocked_paths", [])
        ]
        self.require_hitm: bool = security.get("require_hitm_outside_workspace", True)
        # Blue Zone: when True, all write/delete ops are blocked globally
        self.read_only: bool = security.get("read_only_mode", False)

        # Workspace root
        workspace = cfg.get("agent", {}).get("workspace", "workspace")
        self.workspace_root: Path = Path(workspace).resolve()

    def check_path(self, path_str: str, operation: str = "read") -> Tuple[bool, str]:
        """Check if an operation on a path is allowed.

        Returns: (allowed, message)
        """
        if not self.enabled:
            return True, "Guard disabled."

        try:
            # 1. Canonicalize the path. Relative paths are tool-facing paths and
            # 1. Handle relative paths by resolving them against workspace_root
            p = Path(path_str)
            if not p.is_absolute():
                target = (self.workspace_root / p).resolve()
            else:
                target = p.resolve()
        except Exception as e:
            return False, f"Invalid path: {e}"

        # 2. Check RED ZONE (Blocked)
        for blocked in self.blocked_paths:
            try:
                if target == blocked or blocked in target.parents:
                    return (
                        False,
                        f"SECURITY POLICY: Access to '{target}' is blocked by config.",
                    )
            except Exception:
                continue

        # 3. BLUE ZONE — read-only mode: block ALL write/delete ops globally
        if self.read_only and operation != "read":
            return (
                False,
                "READ_ONLY_MODE: Blue Zone is active — write and delete operations "
                "are blocked system-wide. Switch zone to allow modifications.",
            )

        # 4. Check GREEN ZONE (Workspace)
        try:
            if target == self.workspace_root or self.workspace_root in target.parents:
                return True, "Workspace access allowed."
        except Exception:
            pass

        # 5. Check YELLOW ZONE (Other)
        if operation == "read":
            return True, "Read-only access allowed outside workspace."

        # Write/Delete outside workspace
        if self.require_hitm:
            return False, "HITM_REQUIRED"

        return (
            True,
            "Outside-workspace modification allowed by config.",
        )

    def ask_human(self, path: str, operation: str) -> bool:
        """Prompt the human for confirmation."""
        if self.cfg.get("agent", {}).get("auto_confirm") is True:
            logger.info(f"Auto-confirming action: {operation} on '{path}' (auto_confirm enabled)")
            return True
        if self.on_confirm:
            return self.on_confirm(path, operation)

        # Default CLI implementation (blocking)
        from core.runtime_ui import C
        logger.info(f"\n{C.RED}▲ STOP — SECURITY GUARDRAIL{C.RESET}")
        logger.info(
            f"The agent is attempting a {C.BOLD}{operation.upper()}{C.RESET} action outside the workspace."
        )
        logger.info(f"Target Path: {C.CYAN}{path}{C.RESET}")
        logger.info(
            f"{C.GRAY}(You can allow this once, or modify config.yaml to change security rules){C.RESET}"
        )
        try:
            ans = input("\nDo you allow this specific action? [y/N]: ").strip().lower()
            return ans == "y"
        except (KeyboardInterrupt, EOFError):
            return False
