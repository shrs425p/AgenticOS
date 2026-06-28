import os
from pathlib import Path
from typing import Dict, List, Tuple, Callable, Optional
from kernel.log import get_logger
logger = get_logger(__name__)


def resolve_with_symlink_depth(path: Path, max_depth: int = 5) -> Path:
    """Resolve a path while ensuring we traverse no more than max_depth symlinks."""
    current = Path(path.anchor)
    parts = list(path.parts)[1:] if path.is_absolute() else list(path.parts)
    
    depth = 0
    for part in parts:
        current = current / part
        
        # Resolve symlink components recursively
        while current.is_symlink():
            depth += 1
            if depth > max_depth:
                raise ValueError(f"SECURITY POLICY: Symlink traversal depth exceeded limit of {max_depth}")
            
            target = Path(os.readlink(str(current)))
            if not target.is_absolute():
                current = Path(os.path.normpath(str(current.parent / target)))
            else:
                current = Path(os.path.normpath(str(target)))
                
    return current.resolve()


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
            # 1. Canonicalize the path using custom resolution with symlink depth limit
            p = Path(path_str)
            if not p.is_absolute():
                target_base = self.workspace_root / p
            else:
                target_base = p
            target = resolve_with_symlink_depth(target_base, max_depth=5)
        except ValueError as ve:
            return False, str(ve)
        except Exception as e:
            return False, f"Invalid path: {e}"

        # 1.5. Advanced Enterprise-Grade Sensitive Shielding
        name = target.name.lower()
        parts = [part.lower() for part in target.parts]
        
        # Shielded: .env (read/write/delete blocked)
        if name == ".env" or ".env" in parts:
            return False, "SECURITY POLICY: Access to environment credential file '.env' is strictly blocked."
            
        # Shielded: .git (read/write/delete blocked)
        if ".git" in parts:
            return False, "SECURITY POLICY: Access to Git repository internals '.git' is strictly blocked."
            
        # Shielded: cfg.yaml and cfg/ directory (write/delete blocked)
        if operation != "read":
            if name == "cfg.yaml" or "cfg.yaml" in parts:
                return False, "SECURITY POLICY: Modifying system configuration 'cfg.yaml' is strictly blocked."
            if "cfg" in parts:
                return False, "SECURITY POLICY: Modifying system configuration directory 'cfg/' is strictly blocked."
                
            # Tamper-proof: logs (write/delete blocked)
            if "logs" in parts:
                return False, f"SECURITY POLICY: Direct modification or deletion of audit logs inside '{target}' is strictly blocked to maintain a tamper-proof audit trail."

        # 2. Check RED ZONE (Blocked)
        for blocked in self.blocked_paths:
            try:
                if target == blocked or blocked in target.parents:
                    return (
                        False,
                        f"SECURITY POLICY: Access to '{target}' is blocked by cfg.",
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
            "Outside-workspace modification allowed by cfg.",
        )

    def ask_human(self, path: str, operation: str) -> bool:
        """Prompt the human for confirmation."""
        if self.cfg.get("agent", {}).get("auto_confirm") is True:
            logger.info(f"Auto-confirming action: {operation} on '{path}' (auto_confirm enabled)")
            return True
        if self.on_confirm:
            return self.on_confirm(path, operation)

        # Default CLI implementation (blocking)
        from kernel.ui import C
        logger.info(f"\n{C.RED}▲ STOP — SECURITY GUARDRAIL{C.RESET}")
        logger.info(
            f"The agent is attempting a {C.BOLD}{operation.upper()}{C.RESET} action outside the workspace."
        )
        logger.info(f"Target Path: {C.CYAN}{path}{C.RESET}")
        logger.info(
            f"{C.GRAY}(You can allow this once, or modify cfg.yaml to change security rules){C.RESET}"
        )
        try:
            ans = input("\nDo you allow this specific action? [y/N]: ").strip().lower()
            return ans == "y"
        except (KeyboardInterrupt, EOFError):
            return False
