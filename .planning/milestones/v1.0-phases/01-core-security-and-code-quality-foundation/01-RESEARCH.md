# Phase 1 Research: Core Security and Code Quality Foundation

This document outlines the implementation plan and architectural specifications for Phase 1: Core Security and Code Quality Foundation.

---

## 1. Unicode & Hex Escape Sequence Detection (SEC-01)

### The Threat
Attackers use Unicode escape sequences (e.g., `\u0041` or `U+0041`), hex escape sequences (e.g., `\x41`), and PowerShell character casts (e.g., `[char]0x41` or `[char]65`) to bypass basic regex filter string matching.

### Mitigation Strategy
We must intercept command execution at the entry point in `ops/terminal/safety.py` inside `SafetyMixin._blocked_command_reason`. The check must run **both** on the raw command string (pre-tokenization) and on individual arguments (post-tokenization) to prevent double-decoding or shell token evasion.

### Detailed Regex Formulations
We will define static regex patterns to detect these obfuscation variants:

```python
import re

# 1. Unicode escape sequences: matches \uXXXX, \UXXXXXXXX, or U+XXXX (case-insensitive)
UNICODE_ESCAPE_PAT = re.compile(r"(?i)\\u[0-9a-f]{4}|\\U[0-9a-f]{8}|U\+[0-9a-f]{4,6}")

# 2. Hex escape sequences: matches \xXX (case-insensitive)
HEX_ESCAPE_PAT = re.compile(r"(?i)\\x[0-9a-f]{2}")

# 3. PowerShell char cast expressions: matches [char]0xXX, [char]XX (with optional spacing)
PS_CHAR_CAST_PAT = re.compile(r"(?i)\[char\]\s*(?:0x[0-9a-f]+|\d+)")
```

### Integration in `SafetyMixin._blocked_command_reason`
Add the following checks at the beginning of `_blocked_command_reason(self, command: str) -> str`:

```python
def _blocked_command_reason(self, command: str) -> str:
    if not command:
        return ""
        
    cmd_str = command.strip()

    # Pre-tokenization checks for obfuscation
    if UNICODE_ESCAPE_PAT.search(cmd_str):
        return "SECURITY POLICY: Unicode escape sequence detected in command."
        
    if HEX_ESCAPE_PAT.search(cmd_str):
        return "SECURITY POLICY: Hex character escape sequence detected in command."
        
    if PS_CHAR_CAST_PAT.search(cmd_str):
        return "SECURITY POLICY: PowerShell character cast detected in command."
```

We will also check tokens after splitting:
```python
    # For token-level checks (in case of double decoding/escaping)
    for token in tokens:
        cleaned_token, _, _ = self._clean_token(token)
        if (UNICODE_ESCAPE_PAT.search(cleaned_token) or 
            HEX_ESCAPE_PAT.search(cleaned_token) or 
            PS_CHAR_CAST_PAT.search(cleaned_token)):
            return f"SECURITY POLICY: Obfuscated escape sequence detected in token: {token}"
```

---

## 2. Code Generation Intercept (SEC-02)

### The Threat
Agents writing shell scripts (`.sh`, `.ps1`, `.bat`) or Python scripts (`.py`) directly to locations outside the workspace root using shell redirection operators (e.g., `>` or `>>`) or utilities like `tee`. This bypasses file-system specific zone restrictions because the writing is done by the shell process rather than a Python file tool.

### Mitigation Strategy
Parse the shell command to extract any redirection targets. If a redirect target ends in a script extension and resolves outside the workspace boundary, we block the command or trigger Human-in-the-loop (HITM) confirmation.

### Redirection Target Extraction
We will parse redirection targets inside `SafetyMixin._blocked_command_reason` (or a helper method `_get_redirection_targets`):

```python
def _get_redirection_targets(self, command: str) -> list[str]:
    targets = []
    # Match standard redirection operators (e.g. > output.py, >> script.sh)
    # This matches > or >> followed by a filename which can be quoted or unquoted
    redirect_regex = r"(?:>>|>)\s*([^\s;&|<>'\"]+|'[^']+'|\"[^\"]+\")"
    for match in re.finditer(redirect_regex, command):
        path_str = match.group(1).strip("'\"")
        targets.append(path_str)
        
    # Match Unix tee or PowerShell Out-File / Set-Content / Add-Content
    # E.g. command | tee file.py, command | Out-File -FilePath file.ps1
    pipe_regex = r"\|\s*(?:tee|tee-object|out-file|set-content|add-content)\s+(?:-filepath\s+)?([^\s;&|<>'\"]+|'[^']+'|\"[^\"]+\")"
    for match in re.finditer(pipe_regex, command, re.IGNORECASE):
        path_str = match.group(1).strip("'\"")
        targets.append(path_str)
        
    return targets
```

### Path Guard Integration
To perform the validation and trigger a prompt, we need the `PathGuard` instance to be accessible inside the terminal safety logic.
We will modify the `TerminalExecutor` initialization to attach the path guard:

```python
# kernel/registry.py
self.term = terminal.TerminalExecutor(
    rules=self.rules,
    custom_keys=cfg.get("custom_keys", {}),
    cfg=self.cfg,
)
# Attach guard reference
self.term.guard = self.guard
```

Inside `SafetyMixin._blocked_command_reason`:
```python
    script_extensions = {".py", ".sh", ".ps1", ".bat", ".cmd", ".vbs", ".js"}
    redirect_targets = self._get_redirection_targets(cmd_str)
    
    for target in redirect_targets:
        target_path = Path(target)
        if target_path.suffix.lower() in script_extensions:
            # Check path via guard
            allowed, msg = self.guard.check_path(str(target_path), operation="write")
            if not allowed:
                if msg == "HITM_REQUIRED":
                    # Prompt the user
                    if not self.guard.ask_human(str(target_path), "write_redirect"):
                        return f"SECURITY POLICY: The user has explicitly DENIED writing a script via redirection to '{target_path}'."
                else:
                    return f"SECURITY POLICY: Blocked writing script outside workspace: {msg}"
```

---

## 3. Fine-Grained Registry Policies (SEC-03)

### Registry Hives & CMD/PowerShell Verbs
Registry modifications occur on Windows via:
1. `reg.exe` (e.g. `reg add`, `reg delete`, `reg import`)
2. PowerShell Cmdlets (e.g. `Set-ItemProperty`, `New-ItemProperty`, `Remove-ItemProperty`, `Set-Item`, `New-Item`, `Remove-Item`)

### Policy Schema in `.planning/cfg.json`
We will introduce a registry policy configuration section to `.planning/cfg.json`:

```json
  "registry_policies": {
    "allowed_keys": [
      "HKCU\\Software\\AgenticOS\\*"
    ],
    "blocked_keys": [
      "HKLM\\Software\\Microsoft\\Windows\\CurrentVersion\\Run\\*",
      "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run\\*",
      "HKLM\\Software\\Microsoft\\Windows\\CurrentVersion\\RunOnce\\*",
      "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\RunOnce\\*",
      "HKLM\\System\\CurrentControlSet\\Services\\*"
    ],
    "approval_required_keys": [
      "HKLM\\Software\\*"
    ]
  }
```

### Extraction and Normalization of Keys
Registry keys are normalized by mapping standard abbreviations:
- `HKEY_LOCAL_MACHINE` $\rightarrow$ `HKLM`
- `HKEY_CURRENT_USER` $\rightarrow$ `HKCU`
- `HKEY_CLASSES_ROOT` $\rightarrow$ `HKCR`
- `HKEY_USERS` $\rightarrow$ `HKU`
- `HKEY_CURRENT_CONFIG` $\rightarrow$ `HKCC`
- PowerShell Drive names: `HKLM:\` or `HKCU:\` $\rightarrow$ `HKLM\` or `HKCU\`

### Validation Implementation in Python
Add a helper class `RegistryGuard` or implement methods directly on `PathGuard` / `SafetyMixin`:

```python
import fnmatch

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
        policies = cfg.get("registry_policies", {})
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
        }
        for full, abbrev in replacements.items():
            if key.startswith(full):
                key = key.replace(full, abbrev, 1)
        return key.strip("\\")

    def check_key(self, key_str: str) -> tuple[bool, str]:
        normalized = self.normalize_key(key_str)
        
        # 1. Check default blocked keys
        for pattern in self.DEFAULT_BLOCKED:
            if fnmatch.fnmatch(normalized, pattern):
                return False, f"SECURITY POLICY: Modification of system critical key '{key_str}' is strictly blocked."

        # 2. Check cfg blocked keys
        for pattern in self.blocked:
            if fnmatch.fnmatch(normalized, pattern):
                return False, f"SECURITY POLICY: Key '{key_str}' is explicitly blocked by cfg."

        # 3. Check allowed keys
        for pattern in self.allowed:
            if fnmatch.fnmatch(normalized, pattern):
                return True, "Allowed"

        # 4. Check approval keys
        for pattern in self.approval:
            if fnmatch.fnmatch(normalized, pattern):
                return False, "HITM_REQUIRED"

        # Default fallback: Require approval for modification
        return False, "HITM_REQUIRED"
```

In `SafetyMixin._blocked_command_reason`, look for `reg` and registry cmdlets, parse the path arguments, and run `RegistryGuard.check_key`. If it returns `"HITM_REQUIRED"`, call `self.guard.ask_human(key_path, "registry_edit")`.

---

## 4. Symlink Depth Validation (SEC-04)

### The Threat
Symlink traversal attacks use chains of symlinks (or directory junctions) to point to files outside the workspace, evading traditional path prefix checking.

### Resolution Depth Boundary
We enforce a strict depth limit of **5 resolved symlinks** per operation.

### Custom Resolution Function
We will implement custom path resolution in `kernel/guard.py` to trace symlinks step-by-step:

```python
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
                current = (current.parent / target).resolve()
            else:
                current = target.resolve()
                
    return current.resolve()
```

### Integration in `PathGuard.check_path`
Replace the standard `.resolve()` logic in `kernel/guard.py` (lines 35-42) with:

```python
        try:
            p = Path(path_str)
            if not p.is_absolute():
                target_base = self.workspace_root / p
            else:
                target_base = p
            
            # Custom resolution with symlink depth limit
            target = resolve_with_symlink_depth(target_base, max_depth=5)
        except ValueError as ve:
            return False, str(ve)
        except Exception as e:
            return False, f"Invalid path resolution: {e}"
```

---

## 5. Modular Core Architecture (QUAL-01, QUAL-02, QUAL-03)

### Current Architecture Gaps
The `kernel/cli.py` file is monolithic (119KB), containing orchestration loop code, CLI interfaces, and tool execution blocks. This introduces tight coupling and makes it difficult to add unit spec or reuse logic.

### Modular Core Directory Layout
We will split `kernel/cli.py` into distinct, focused sub-modules:

```
kernel/
├── __init__.py
├── orchestrator.py    # Main agent execution loop and session management
├── dispatcher.py      # Action verification and dispatching logic
├── errors.py          # Unified AgentError and custom exception types
├── toolbase.py       # Tool protocol and Pydantic validation schemas
└── tool_registry.py   # Registry manager (updated to resolve circular imports)
```

### Type-Safe `Tool` Protocol & Schemas
We will define a type-safe tool execution interface inside `kernel/base.py` using Pydantic:

```python
from typing import Protocol, Callable, Any, Dict
from pydantic import BaseModel, Field

class ToolMetadata(BaseModel):
    name: str = Field(..., description="The name of the tool")
    description: str = Field(..., description="A short description of what the tool does")
    category: str = Field("General", description="Tool category classification")
    version: str = Field("1.0.0", description="Version string")
    author: str = Field("AgenticOS", description="Author identifier")

class Tool(Protocol):
    metadata: ToolMetadata
    func: Callable
    
    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Execute the tool function directly."""
        ...
```

The registry will store instances of objects matching the `Tool` interface:
```python
class RegisteredTool:
    def __init__(self, metadata: ToolMetadata, func: Callable):
        self.metadata = metadata
        self.func = func
        
    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self.func(*args, **kwargs)
```

### Dynamic Tool Registration
To eliminate circular imports, `kernel/registry.py` will not import subsystems at the top level. Instead, subsystems will be loaded dynamically or registered via decorator discovery during registry instantiation:

```python
class ToolRegistry:
    def _register_all(self):
        # Dynamically import and register default subsystems to avoid circular loops
        subsystems = [
            ("ops.files", "FileManager", "Files"),
            ("ops.shell", "TerminalExecutor", "Terminal"),
            ("ops.web", "WebTools", "Web"),
            ("ops.notify", "NotificationCenter", "General"),
            ("ops.screen", "ScreenManager", "General"),
            ("ops.ocr", "OCRManager", "Media"),
            ("ops.system", "SystemManager", "System")
        ]
        
        for module_path, class_name, category in subsystems:
            try:
                module = importlib.import_module(module_path)
                cls = getattr(module, class_name)
                # Instantiate subsystem passing cfg & rules
                instance = cls(rules=self.rules, cfg=self.cfg)
                self._register_subsystem(instance, category)
            except Exception as e:
                logging.exception(f"Failed to load subsystem {class_name}: {e}")
```

---

## 6. Unified `AgentError` Class (QUAL-04)

### Structure & Fields
We will define `AgentError` inside `kernel/errors.py` as a subclass of `Exception`:

```python
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
            res += f"\nSuggestions: " + "; ".join(self.suggestions)
        return res
```

### Integration
- Wherever commands or paths fail security checks, raise `AgentError` with code `SECURITY_VIOLATION` or `PATH_TRAVERSAL`.
- The main orchestration loop in `kernel/agent.py` will catch `AgentError`, format it cleanly for the LLM context, and display it with appropriate recommendations.

---

## 7. Threats & Mitigations Matrix (DOC-02)

| Threat / Vulnerability Vector | Mitigation Mechanism | Verification Metric / Test (TEST-05) |
| --- | --- | --- |
| **Unicode / Hex Obfuscation** | Input command inspection for `\u`, `\x`, `[char]` patterns | Pass obfuscated execution commands to `SafetyMixin` and assert block. |
| **Command-based Script Redirection** | Command redirection parsing & path validation | Intercept command `echo ... > outside.py` and confirm PathGuard block. |
| **Registry Tampering** | Config-driven `RegistryGuard` with system key blocklist | Assert modifications to critical keys (e.g. Run/RunOnce/Services) are blocked. |
| **Symlink Directory Loops** | Custom step-by-step path resolution limit of 5 | Create symlink path with depth > 5 and verify traversal limit block. |

---

## 8. Verification Strategy & Security Regression Suite (TEST-05)

We will implement a security validation suite in `spec/test_security_foundation.py` verifying the following:
1. **Unicode/Hex Block Tests**: Assert that inputs like `powershell -c "$([char]0x41)$([char]0x6d)"` or `echo -e "\x41"` trigger a `SECURITY POLICY` error.
2. **Redirection Intercept Tests**: Assert that commands running script redirects (`> /tmp/malicious.py`) outside the workspace root are blocked or raise a PathGuard violation.
3. **Registry Policy Tests**: Verify modifying `HKLM\Software\Microsoft\Windows\CurrentVersion\Run` is rejected with registry tampering errors.
4. **Symlink Depth Tests**: Mock a deep symlink structure (> 5 links) and verify that resolution raises a `ValueError` with `Symlink traversal depth exceeded`.
