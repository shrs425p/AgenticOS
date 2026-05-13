from pathlib import Path
from typing import Dict, List, Tuple, Callable, Optional


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
            # 1. Canonicalize the path
            target = Path(path_str).resolve()
        except Exception as e:
            return False, f"Invalid path: {e}"

        # 2. Check RED ZONE (Blocked)
        for blocked in self.blocked_paths:
            try:
                if target == blocked or blocked in target.parents:
                    return (
                        False,
                        f"SECURITY ALERT: Access to system path '{target}' is strictly forbidden.",
                    )
            except Exception:
                continue

        # 3. Check GREEN ZONE (Workspace)
        try:
            if target == self.workspace_root or self.workspace_root in target.parents:
                return True, "Workspace access allowed."
        except Exception:
            pass

        # 4. Check YELLOW ZONE (Other)
        if operation == "read":
            return True, "Read-only access allowed outside workspace."

        # Write/Delete outside workspace
        if self.require_hitm:
            return False, "HITM_REQUIRED"

        return (
            False,
            f"SECURITY POLICY: Modification of '{target}' is forbidden. This path is outside the allowed workspace. Do not attempt to bypass this with elevated privileges or attribute changes.",
        )

    def ask_human(self, path: str, operation: str) -> bool:
        """Prompt the human for confirmation."""
        if self.on_confirm:
            return self.on_confirm(path, operation)

        # Default CLI implementation (blocking)
        print("\n\033[91m🛑 SECURITY GUARDRAIL\033[0m")
        print(
            f"The agent is attempting a \033[1m{operation.upper()}\033[0m action outside the workspace."
        )
        print(f"Target Path: \033[36m{path}\033[0m")
        print(
            "\033[90m(You can allow this once, or modify config.yaml to change security rules)\033[0m"
        )
        try:
            ans = input("\nDo you allow this specific action? [y/N]: ").strip().lower()
            return ans == "y"
        except (KeyboardInterrupt, EOFError):
            return False
