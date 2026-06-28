"""Module for safety.py"""

from __future__ import annotations

import os
import re
import shlex
import fnmatch
from pathlib import Path


class RegistryGuard:
    DEFAULT_BLOCKED = [
        "HKLM\\SOFTWARE\\MICROSOFT\\WINDOWS\\CURRENTVERSION\\RUN\\*",
        "HKLM\\SOFTWARE\\MICROSOFT\\WINDOWS\\CURRENTVERSION\\RUNONCE\\*",
        "HKCU\\SOFTWARE\\MICROSOFT\\WINDOWS\\CURRENTVERSION\\RUN\\*",
        "HKCU\\SOFTWARE\\MICROSOFT\\WINDOWS\\CURRENTVERSION\\RUNONCE\\*",
        "HKLM\\SYSTEM\\CURRENTCONTROLSET\\SERVICES\\*",
        "HKLM\\SOFTWARE\\MICROSOFT\\WINDOWS NT\\CURRENTVERSION\\WINLOGON\\*"
    ]

    def __init__(self, cfg: dict):
        policies = cfg.get("registry_policies") or cfg.get("policy", {}).get("registry_policies", {}) or {}
        self.allowed = [k.upper() for k in policies.get("allowed_keys", [])]
        self.blocked = [k.upper() for k in policies.get("blocked_keys", [])]
        self.approval = [k.upper() for k in policies.get("approval_required_keys", [])]

    def normalize_key(self, key_str: str) -> str:
        key = key_str.upper().replace("/", "\\").replace("REGISTRY::", "")
        replacements = {
            "HKEY_LOCAL_MACHINE": "HKLM",
            "HKEY_CURRENT_USER": "HKCU",
            "HKEY_CLASSES_ROOT": "HKCR",
            "HKEY_USERS": "HKU",
            "HKEY_CURRENT_CONFIG": "HKCC",
            "HKLM:": "HKLM",
            "HKCU:": "HKCU",
            "HKCR:": "HKCR",
            "HKU:": "HKU",
            "HKCC:": "HKCC",
        }
        for full, abbrev in replacements.items():
            if key.startswith(full):
                key = abbrev + key[len(full):]
        return key.strip("\\")

    def check_key(self, key_str: str) -> tuple[bool, str]:
        normalized = self.normalize_key(key_str)
        normalized_with_slash = normalized + "\\"
        
        # 1. Check default blocked keys
        for pattern in self.DEFAULT_BLOCKED:
            if fnmatch.fnmatch(normalized, pattern) or fnmatch.fnmatch(normalized_with_slash, pattern):
                return False, f"SECURITY POLICY: Modification of system critical key '{key_str}' is strictly blocked."

        # 2. Check cfg blocked keys
        for pattern in self.blocked:
            if fnmatch.fnmatch(normalized, pattern) or fnmatch.fnmatch(normalized_with_slash, pattern):
                return False, f"SECURITY POLICY: Key '{key_str}' is explicitly blocked by cfg."

        # 3. Check allowed keys
        for pattern in self.allowed:
            if fnmatch.fnmatch(normalized, pattern) or fnmatch.fnmatch(normalized_with_slash, pattern):
                return True, "Allowed"

        # 4. Check approval keys
        for pattern in self.approval:
            if fnmatch.fnmatch(normalized, pattern) or fnmatch.fnmatch(normalized_with_slash, pattern):
                return False, "HITM_REQUIRED"

        # Default fallback: Require approval for modification
        return False, "HITM_REQUIRED"


class SafetyMixin:
    """Mixin class for terminal command execution safety validation."""

    _VAR_PATTERNS = [
        re.compile(r"%[a-zA-Z0-9_-]+%"),
        re.compile(r"\$[a-zA-Z0-9_-]+"),
        re.compile(r"\$\{[a-zA-Z0-9_-]+\}"),
        re.compile(r"\$env:[a-zA-Z0-9_-]+", re.IGNORECASE),
    ]
    _UNICODE_ESCAPE_PAT = re.compile(r"(?i)\\u[0-9a-f]{4}|\\U[0-9a-f]{8}|U\+[0-9a-f]{4,6}")
    _HEX_ESCAPE_PAT = re.compile(r"(?i)\\x[0-9a-f]{2}")
    _PS_CHAR_CAST_PAT = re.compile(r"(?i)\[char\]\s*(?:0x[0-9a-f]+|\d+)")
    _PS_REGISTRY_WRITE_CMDLETS = {
        "set-itemproperty", "new-itemproperty", "remove-itemproperty",
        "set-item", "new-item", "remove-item",
        "rename-itemproperty", "copy-itemproperty", "move-itemproperty",
        "clear-itemproperty", "rename-item", "copy-item", "move-item",
        "clear-item"
    }

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
        is_windows = getattr(self, "system", "Windows" if os.name == "nt" else "Linux") == "Windows"
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
            # characters, underskernels, or hyphens, then using internal quotes
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
        # Normalize backslashes to forward slashes for cross-platform basename extraction
        normalized = token.replace("\\", "/")
        base = normalized.split("/")[-1]
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

    def _extract_registry_path(self, tokens: list[str]) -> str | None:
        path_indicators = {"HKLM", "HKCU", "HKCR", "HKU", "HKCC", "HKEY_"}
        for i, token in enumerate(tokens):
            t_upper = token.upper()
            if t_upper in {"-PATH", "-LITERALPATH"} or t_upper.startswith("-PAT"):
                if i + 1 < len(tokens):
                    next_t = tokens[i + 1]
                    next_t_upper = next_t.upper()
                    if any(ind in next_t_upper for ind in path_indicators) or "REGISTRY::" in next_t_upper:
                        return next_t
            if any(ind in t_upper for ind in path_indicators) or "REGISTRY::" in t_upper:
                return token
        return None

    def _blocked_command_reason(self, command: str) -> str:
        """Check if a command is blocked by the configured safety rules.

        Args:
            command: The command line string to validate.

        Returns:
            A string descriclig the block reason, or empty string if allowed.
        """
        if not self.rules.get("allow_shell_exec", True):
            return "shell execution is disabled"

        if not self.rules.get("validate_commands", False):
            return ""

        is_windows = getattr(self, "system", "Windows" if os.name == "nt" else "Linux") == "Windows"
        cmd_str = command or ""

        # Pre-tokenization checks for obfuscation escapes
        if self._UNICODE_ESCAPE_PAT.search(cmd_str):
            return "Command blocked by safety rules: Unicode escape sequence detected"
        if self._HEX_ESCAPE_PAT.search(cmd_str):
            return "Command blocked by safety rules: Hex character escape sequence detected"
        if self._PS_CHAR_CAST_PAT.search(cmd_str):
            return "Command blocked by safety rules: PowerShell character cast detected"

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
            cleaned_t, _, _ = self._clean_token(t)
            if (self._UNICODE_ESCAPE_PAT.search(cleaned_t) or
                self._HEX_ESCAPE_PAT.search(cleaned_t) or
                self._PS_CHAR_CAST_PAT.search(cleaned_t)):
                return f"Command blocked by safety rules: obfuscated escape sequence detected in token: {t}"

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
            cmd_lower = cmd_str.lower()
            if "microsoft.win32.registry" in cmd_lower:
                return "Command blocked by safety rules: .NET registry API access is prohibited."
            if "stdregprov" in cmd_lower:
                return "Command blocked by safety rules: WMI registry provider access is prohibited."

        if verb == "reg" and len(cleaned_tokens) > 1:
            subaction = cleaned_tokens[1].lower()
            if subaction in {"add", "delete", "import"}:
                if not self.rules.get("allow_registry_edit", False):
                    return f"Command blocked by safety rules: reg {subaction}"
                
                # Apply fine-grained registry policies
                guard = RegistryGuard(self.cfg)
                if subaction == "import":
                    path_guard = getattr(self, "guard", None)
                    if path_guard:
                        if not path_guard.ask_human("all_registry_keys", "registry_import"):
                            return "Command blocked by safety rules: registry import was denied by user."
                    else:
                        return "Command blocked by safety rules: registry import requires user approval."
                elif len(cleaned_tokens) > 2:
                    key_path = cleaned_tokens[2]
                    allowed, msg = guard.check_key(key_path)
                    if not allowed:
                        if msg == "HITM_REQUIRED":
                            path_guard = getattr(self, "guard", None)
                            if path_guard:
                                if not path_guard.ask_human(key_path, "registry_edit"):
                                    return f"Command blocked by safety rules: registry edit was denied by user: {key_path}"
                            else:
                                return f"Command blocked by safety rules: registry edit requires user approval: {key_path}"
                        else:
                            return msg

        elif verb in self._PS_REGISTRY_WRITE_CMDLETS:
            reg_path = self._extract_registry_path(cleaned_tokens)
            if reg_path or verb == "set-itemproperty": # set-itemproperty is explicitly a registry cmdlet
                if not self.rules.get("allow_registry_edit", False):
                    return f"Command blocked by safety rules: {verb}"
                
                if reg_path:
                    guard = RegistryGuard(self.cfg)
                    allowed, msg = guard.check_key(reg_path)
                    if not allowed:
                        if msg == "HITM_REQUIRED":
                            path_guard = getattr(self, "guard", None)
                            if path_guard:
                                if not path_guard.ask_human(reg_path, "registry_edit"):
                                    return f"Command blocked by safety rules: registry edit was denied by user: {reg_path}"
                            else:
                                return f"Command blocked by safety rules: registry edit requires user approval: {reg_path}"
                        else:
                            return msg
                else:
                    path_guard = getattr(self, "guard", None)
                    if path_guard:
                        if not path_guard.ask_human("unknown_registry_path", "registry_edit"):
                            return f"Command blocked by safety rules: registry edit cmdlet {verb} was denied by user."
                    else:
                        return f"Command blocked by safety rules: registry edit cmdlet {verb} requires user approval."

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
            if verb in {
                "stop-service", "start-service", "restart-service",
                "set-service", "suspend-service", "resume-service", "new-service"
            }:
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

        # Step 7: Check redirection script writing targets
        script_extensions = {".py", ".sh", ".ps1", ".bat", ".cmd", ".vbs", ".js"}
        redirect_targets = self._get_redirection_targets(cmd_str)
        for target in redirect_targets:
            target_path = Path(target)
            if target_path.suffix.lower() in script_extensions:
                guard = getattr(self, "guard", None)
                if guard:
                    allowed, msg = guard.check_path(str(target_path), operation="write")
                    if not allowed:
                        if msg == "HITM_REQUIRED":
                            if not guard.ask_human(str(target_path), "write_redirect"):
                                return f"Command blocked by safety rules: writing script via redirection was denied by user: {target_path}"
                        else:
                            return f"Command blocked by safety rules: blocked writing script outside workspace: {msg}"

        return ""

    def _get_redirection_targets(self, command: str) -> list[str]:
        targets = []
        # Match standard redirection operators (e.g. > output.py, >> script.sh)
        redirect_regex = r"(?:>>|>)\s*([^\s;&|<>'\"]+|'[^']+'|\"[^\"]+\")"
        for match in re.finditer(redirect_regex, command):
            path_str = match.group(1).strip("'\"")
            targets.append(path_str)
            
        # Match Unix tee or PowerShell Out-File / Set-Content / Add-Content
        pipe_regex = r"\|\s*(?:tee|tee-object|out-file|set-content|add-content)\s+(?:-filepath\s+)?([^\s;&|<>'\"]+|'[^']+'|\"[^\"]+\")"
        for match in re.finditer(pipe_regex, command, re.IGNORECASE):
            path_str = match.group(1).strip("'\"")
            targets.append(path_str)
            
        return targets
