"""Module for safety.py"""

from __future__ import annotations

import os
import re
import shlex


class SafetyMixin:
    """Mixin class for terminal command execution safety validation."""

    _VAR_PATTERNS = [
        re.compile(r"%[a-zA-Z0-9_-]+%"),
        re.compile(r"\$[a-zA-Z0-9_-]+"),
        re.compile(r"\$\{[a-zA-Z0-9_-]+\}"),
        re.compile(r"\$env:[a-zA-Z0-9_-]+", re.IGNORECASE),
    ]

    def _clean_token(self, token: str) -> tuple[str, bool, bool]:
        """Strip outer matching quotes, check internal quotes and escapes.

        Args:
            token: The raw token string.

        Returns:
            A tuple containing:
                - The fully cleaned token (quotes and escapes removed).
                - A boolean indicating if internal quotes exist.
                - A boolean indicating if internal escapes exist.
        """
        if not token:
            return "", False, False
        # Recursively strip wrapping quote layers
        cleaned = token
        while len(cleaned) >= 2:
            if cleaned.startswith("'") and cleaned.endswith("'"):
                cleaned = cleaned[1:-1]
            elif cleaned.startswith('"') and cleaned.endswith('"'):
                cleaned = cleaned[1:-1]
            else:
                break

        # Check for internal quotes
        has_internal_quotes = "'" in cleaned or '"' in cleaned

        # Clean quotes
        cleaned_no_quotes = cleaned.replace("'", "").replace('"', "")

        # Check for escape characters platform-specifically
        is_windows = os.name == "nt"
        has_escapes = False
        if is_windows:
            has_escapes = "^" in cleaned_no_quotes or "`" in cleaned_no_quotes
            final_cleaned = cleaned_no_quotes.replace("^", "").replace("`", "")
        else:
            has_escapes = "\\" in cleaned_no_quotes
            final_cleaned = cleaned_no_quotes.replace("\\", "")

        return final_cleaned, has_internal_quotes, has_escapes

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
        """Identify if a token uses quote or escape obfuscation.

        Args:
            token: The token string to check.

        Returns:
            True if the token contains suspicious internal quotes or escapes, False otherwise.
        """
        cleaned, has_internal_quotes, has_escapes = self._clean_token(token)
        if has_internal_quotes or has_escapes:
            # If the raw cleaned string consists entirely of alphanumeric
            # characters, underscores, or hyphens, then using internal quotes
            # or escapes is suspicious and flagged as obfuscation.
            if re.match(r"^[a-zA-Z0-9_-]+$", cleaned):
                return True
        return False

    def _contains_variable(self, token: str) -> bool:
        """Check if a token contains environment variable or parameter lookups.

        Args:
            token: The token to check.

        Returns:
            True if the token contains a variable lookup pattern.
        """
        for pattern in self._VAR_PATTERNS:
            if pattern.search(token):
                return True
        return False

    def _has_chaining_operators(
        self, command: str, is_windows: bool
    ) -> tuple[bool, str]:
        """Scan command string for unquoted chaining operators.

        Args:
            command: The command line string to scan.
            is_windows: True if executing on Windows.

        Returns:
            A tuple of (has_operators, matched_operator_string).
        """
        in_single = False
        in_double = False
        i = 0
        n = len(command)
        while i < n:
            char = command[i]

            # Handle escape sequences
            if is_windows:
                # Caret (^) escapes the next character in CMD outside quotes
                if char == "^" and not in_single:
                    i += 2
                    continue
            else:
                # Backslash (\) escapes the next character in POSIX shells
                if char == "\\" and not in_single:
                    i += 2
                    continue

            # Handle quotes
            if char == "'" and not in_double:
                in_single = not in_single
                i += 1
            elif char == '"' and not in_single:
                in_double = not in_double
                i += 1
            elif not in_single and not in_double:
                # Check for $() subshell
                if char == "$" and i + 1 < n and command[i + 1] == "(":
                    return True, "$("
                # Check for single character operators
                chaining_chars = {";", "|", "&"} if is_windows else {";", "|", "&", "`"}
                if char in chaining_chars:
                    op = char
                    if i + 1 < n and command[i + 1] == char and char in {"&", "|"}:
                        op = char + char
                    return True, op
                i += 1
            else:
                i += 1
        return False, ""

    def _get_command_verb(self, token: str) -> str:
        """Extract the base command verb from a token.

        Args:
            token: The command token (e.g. an executable path).

        Returns:
            The lowercase base name of the command without .exe extension.
        """
        # Handle both Windows and POSIX path separators to correctly extract basename
        import ntpath
        import posixpath
        base = ntpath.basename(token)
        if "\\" not in token and "/" in token:
             base = posixpath.basename(token)

        if base.lower().endswith(".exe"):
            base = base[:-4]
        return base.lower()

    def _is_powershell_command_flag(self, token: str) -> bool:
        """Check if a token is a PowerShell command parameter.

        Args:
            token: The parameter token to check.

        Returns:
            True if it matches a prefix of 'command' ignoring leading hyphen/slash.
        """
        if not (token.startswith("-") or token.startswith("/")):
            return False
        flag = token[1:].lower()
        return len(flag) >= 1 and "command".startswith(flag)

    def _is_powershell_encoded_flag(self, token: str) -> bool:
        """Check if a token is a PowerShell base64 encoded parameter.

        Args:
            token: The parameter token to check.

        Returns:
            True if it matches a prefix of 'encodedcommand' ignoring leading hyphen/slash.
        """
        if not (token.startswith("-") or token.startswith("/")):
            return False
        flag = token[1:].lower()
        return len(flag) >= 2 and "encodedcommand".startswith(flag)

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

        is_windows = os.name == "nt"
        cmd_str = command or ""

        # Step 1: Pre-tokenization check for shell chaining operators
        has_chain, chain_op = self._has_chaining_operators(cmd_str, is_windows)
        if has_chain:
            return f"Command blocked by safety rules: shell chaining operator detected ({chain_op})"

        # Step 2: Tokenize structurally using shlex
        try:
            # On Windows, use posix=False to preserve backslashes in folder paths.
            tokens = shlex.split(cmd_str, posix=not is_windows)
            # Use posix=False to preserve escapes for obfuscation check
            obfuscation_tokens = (
                shlex.split(cmd_str, posix=False) if not is_windows else tokens
            )
        except Exception as e:
            return f"Command blocked by safety rules: shell parsing error ({e})"

        if not tokens:
            return ""

        # Step 3: Clean tokens and check for quote/escape obfuscation
        for t in obfuscation_tokens:
            if self._detect_obfuscation(t):
                return (
                    "Command blocked by safety rules: command obfuscation detected "
                    f"(internal quotes/escapes in token: {t})"
                )

        cleaned_tokens = []
        for t in tokens:
            cleaned_t, _, _ = self._clean_token(t)
            cleaned_tokens.append(cleaned_t)

        if not cleaned_tokens or not cleaned_tokens[0]:
            return ""

        # Step 4: Contextual environment variable check
        # Check first token (command verb position)
        if self._contains_variable(tokens[0]):
            return (
                "Command blocked by safety rules: environment variable expansion "
                f"detected in verb position ({tokens[0]})"
            )

        verb = self._get_command_verb(cleaned_tokens[0])

        # Step 5: Check safety rules against exact command verbs and arguments
        # 5.1 Registry edits
        if not self.rules.get("allow_registry_edit", False):
            if verb == "reg" and len(cleaned_tokens) > 1:
                subaction = cleaned_tokens[1].lower()
                if subaction in {"add", "delete", "import"}:
                    return f"Command blocked by safety rules: reg {subaction}"
            if verb == "set-itemproperty":
                return "Command blocked by safety rules: set-itemproperty"

        # 5.2 Service control
        if not self.rules.get("allow_service_control", False):
            if verb == "sc":
                return "Command blocked by safety rules: sc"
            if verb == "net" and len(cleaned_tokens) > 1:
                subaction = cleaned_tokens[1].lower()
                if subaction in {"start", "stop"}:
                    return f"Command blocked by safety rules: net {subaction}"
            if verb in {"systemctl", "service"}:
                return f"Command blocked by safety rules: {verb}"

        # 5.3 System changes
        if not self.rules.get("allow_system_changes", False):
            if verb in {"shutdown", "restart-computer", "reboot", "format", "diskpart"}:
                return f"Command blocked by safety rules: {verb}"

        # Step 6: Recursive validation for nested commands (e.g. powershell -c, cmd /c)
        for i, token in enumerate(cleaned_tokens):
            # Check powershell wrappers
            if verb in {"powershell", "pwsh"}:
                if self._is_powershell_command_flag(token) and i + 1 < len(tokens):
                    nested_cmd = " ".join(tokens[i + 1 :])
                    nested_cmd = self._strip_wrapping_quotes(nested_cmd)

                    # Contextual variable check: if the nested command parameter is a variable lookup
                    if self._contains_variable(nested_cmd):
                        return (
                            "Command blocked by safety rules: environment variable expansion "
                            f"detected in wrapper parameters ({nested_cmd})"
                        )

                    nested_reason = self._blocked_command_reason(nested_cmd)
                    if nested_reason:
                        return nested_reason
                elif self._is_powershell_encoded_flag(token) and i + 1 < len(tokens):
                    encoded_payload = self._strip_wrapping_quotes(tokens[i + 1])
                    try:
                        import base64

                        decoded_bytes = base64.b64decode(
                            encoded_payload.encode("ascii")
                        )
                        decoded_cmd = decoded_bytes.decode("utf-16-le")
                    except Exception as e:
                        return f"Command blocked by safety rules: base64-decode-failure ({e})"

                    nested_reason = self._blocked_command_reason(decoded_cmd)
                    if nested_reason:
                        return nested_reason
            # Check cmd wrappers
            elif verb == "cmd":
                if token.lower() in {"/c", "/k", "/r"} and i + 1 < len(tokens):
                    nested_cmd = " ".join(tokens[i + 1 :])
                    nested_cmd = self._strip_wrapping_quotes(nested_cmd)

                    # Contextual variable check: if the nested command parameter is a variable lookup
                    if self._contains_variable(nested_cmd):
                        return (
                            "Command blocked by safety rules: environment variable expansion "
                            f"detected in wrapper parameters ({nested_cmd})"
                        )

                    nested_reason = self._blocked_command_reason(nested_cmd)
                    if nested_reason:
                        return nested_reason
            # Check POSIX shell wrappers
            elif verb in {"bash", "sh", "zsh", "dash", "ash"}:
                if token.lower() == "-c" and i + 1 < len(tokens):
                    nested_cmd = " ".join(tokens[i + 1 :])
                    nested_cmd = self._strip_wrapping_quotes(nested_cmd)

                    # Contextual variable check: if the nested command parameter is a variable lookup
                    if self._contains_variable(nested_cmd):
                        return (
                            "Command blocked by safety rules: environment variable expansion "
                            f"detected in wrapper parameters ({nested_cmd})"
                        )

                    nested_reason = self._blocked_command_reason(nested_cmd)
                    if nested_reason:
                        return nested_reason

        return ""
