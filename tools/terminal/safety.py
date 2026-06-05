"""Module for safety.py"""
from __future__ import annotations

import os
import re
import shlex


class SafetyMixin:
    """Mixin class for terminal command execution safety validation."""

    def _clean_token(self, token: str) -> tuple[str, bool]:
        """Strip outer matching quotes recursively and detect internal quote presence.

        Args:
            token: The raw token string to clean.

        Returns:
            A tuple containing:
                - The quote-sanitized string.
                - A boolean indicating if any internal quote structures exist.
        """
        if not token:
            return "", False

        # Detect if there are any quotes
        has_quotes = "'" in token or '"' in token
        if not has_quotes:
            return token, False

        # Recursively strip wrapping quote layers
        cleaned = token
        while len(cleaned) >= 2:
            if cleaned.startswith("'") and cleaned.endswith("'"):
                cleaned = cleaned[1:-1]
            elif cleaned.startswith('"') and cleaned.endswith('"'):
                cleaned = cleaned[1:-1]
            else:
                break

        # If quotes remain after stripping wrapping layers, they are internal
        has_internal = "'" in cleaned or '"' in cleaned

        # Clean all remaining quotes to extract the raw identifier/word
        final_cleaned = cleaned.replace("'", "").replace('"', "")
        return final_cleaned, has_internal

    def _strip_wrapping_quotes(self, s: str) -> str:
        """Strip outermost matching quotes from a string.

        Args:
            s: The string to strip.

        Returns:
            The stripped string.
        """
        cleaned = s.strip()
        while len(cleaned) >= 2:
            if cleaned.startswith("'") and cleaned.endswith("'"):
                cleaned = cleaned[1:-1]
            elif cleaned.startswith('"') and cleaned.endswith('"'):
                cleaned = cleaned[1:-1]
            else:
                break
        return cleaned

    def _detect_obfuscation(self, token: str) -> bool:
        """Identify if a token uses quote obfuscation.

        Args:
            token: The token string to check.

        Returns:
            True if the token contains suspicious internal quotes, False otherwise.
        """
        cleaned, has_internal = self._clean_token(token)
        if has_internal:
            # If the raw cleaned string consists entirely of alphanumeric
            # characters, underscores, or hyphens, the internal quotes are suspicious.
            if re.match(r"^[a-zA-Z0-9_-]+$", cleaned):
                return True
        return False

    def _get_command_verb(self, token: str) -> str:
        """Extract the base command verb from a token.

        Args:
            token: The command token (e.g. an executable path).

        Returns:
            The lowercase base name of the command without .exe extension.
        """
        base = os.path.basename(token)
        if base.lower().endswith(".exe"):
            base = base[:-4]
        return base.lower()

    def _blocked_command_reason(self, command: str) -> str:
        """Check if a command is blocked by the configured safety rules.

        Args:
            command: The command line string to validate.

        Returns:
            A string describing the block reason, or empty string if allowed.
        """
        if not self.rules.get("allow_shell_exec", True):
            return "shell execution is disabled"

        if not self.rules.get("validate_commands", False):
            return ""

        # Step 1: Tokenize structurally using shlex
        is_windows = os.name == "nt"
        try:
            # On Windows, use posix=False to preserve backslashes in folder paths.
            tokens = shlex.split(command or "", posix=not is_windows)
        except Exception as e:
            return f"Command blocked by safety rules: shell parsing error ({e})"

        if not tokens:
            return ""

        # Step 2: Clean tokens and check for quote obfuscation
        cleaned_tokens = []
        for t in tokens:
            if self._detect_obfuscation(t):
                return (
                    "Command blocked by safety rules: command obfuscation detected "
                    f"(internal quotes in token: {t})"
                )
            cleaned_t, _ = self._clean_token(t)
            cleaned_tokens.append(cleaned_t)

        if not cleaned_tokens or not cleaned_tokens[0]:
            return ""

        verb = self._get_command_verb(cleaned_tokens[0])

        # Step 3: Check safety rules against exact command verbs and arguments
        # 3.1 Registry edits
        if not self.rules.get("allow_registry_edit", False):
            if verb == "reg" and len(cleaned_tokens) > 1:
                subaction = cleaned_tokens[1].lower()
                if subaction in {"add", "delete", "import"}:
                    return f"Command blocked by safety rules: reg {subaction}"
            if verb == "set-itemproperty":
                return "Command blocked by safety rules: set-itemproperty"

        # 3.2 Service control
        if not self.rules.get("allow_service_control", False):
            if verb == "sc":
                return "Command blocked by safety rules: sc"
            if verb == "net" and len(cleaned_tokens) > 1:
                subaction = cleaned_tokens[1].lower()
                if subaction in {"start", "stop"}:
                    return f"Command blocked by safety rules: net {subaction}"
            if verb in {"systemctl", "service"}:
                return f"Command blocked by safety rules: {verb}"

        # 3.3 System changes
        if not self.rules.get("allow_system_changes", False):
            if verb in {"shutdown", "restart-computer", "reboot", "format", "diskpart"}:
                return f"Command blocked by safety rules: {verb}"

        # Step 4: Recursive validation for nested commands (e.g. powershell -c, cmd /c)
        for i, token in enumerate(cleaned_tokens):
            # Check powershell wrappers
            if verb in {"powershell", "pwsh"}:
                if token.lower() in {"-command", "-c", "/command", "/c"} and i + 1 < len(tokens):
                    nested_cmd = " ".join(tokens[i + 1:])
                    nested_cmd = self._strip_wrapping_quotes(nested_cmd)
                    nested_reason = self._blocked_command_reason(nested_cmd)
                    if nested_reason:
                        return nested_reason
            # Check cmd wrappers
            elif verb == "cmd":
                if token.lower() in {"/c", "/k", "/r"} and i + 1 < len(tokens):
                    nested_cmd = " ".join(tokens[i + 1:])
                    nested_cmd = self._strip_wrapping_quotes(nested_cmd)
                    nested_reason = self._blocked_command_reason(nested_cmd)
                    if nested_reason:
                        return nested_reason
            # Check POSIX shell wrappers
            elif verb in {"bash", "sh", "zsh", "dash", "ash"}:
                if token.lower() == "-c" and i + 1 < len(tokens):
                    nested_cmd = " ".join(tokens[i + 1:])
                    nested_cmd = self._strip_wrapping_quotes(nested_cmd)
                    nested_reason = self._blocked_command_reason(nested_cmd)
                    if nested_reason:
                        return nested_reason

        return ""
