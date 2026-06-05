# Phase 2: Shell Chaining & Obfuscation Interception - Research

**Researched:** 2026-06-05
**Domain:** Command chaining detection, shell escape obfuscation, and variable expansion interception
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01**: Implement a quote-aware character scanner in `SafetyMixin._blocked_command_reason` to check the raw command string before tokenization. It will flag chaining characters (`&`, `;`, `|`, `` ` ``, and `$(`) if they appear outside of active single or double quotes, preventing evasion via non-spaced operators (e.g. `echo hello;sc stop`) while allowing safe quoted usage (e.g. `echo "hello & welcome"`).
- **D-02**: Enforce contextual variable lookup blocks. Detect environment variables and parameter expansions (`%VAR%`, `$VAR`, `$env:VAR`, `${VAR}`) only if they appear in the command verb position (first token of command/nested command) or inside execution wrapper parameters, allowing benign read-only operations like `echo $PATH` or `echo %USERNAME%`.
- **D-03**: Extend the `_detect_obfuscation` helper to identify caret `^` (CMD), backslash `\` (Bash), and backtick `` ` `` (PowerShell) escapes inside tokens. Block execution if removing these characters from a token reveals a simple word/identifier (e.g., `n^e^t` -> `net`, `s\c` -> `sc`, `n`e`t` -> `net`).
- **D-04**: Keep all validation logic contained within the `SafetyMixin` class in `tools/terminal/safety.py`.

### the agent's Discretion
- Specific warning messages on blocking.
- Unit testing setup and mock command lists.

### Deferred Ideas (OUT OF SCOPE)
- Runner integration and live subprocess interception in `runner.py` — Phase 3.
</user_constraints>

<architectural_responsibility_map>
## Architectural Responsibility Map

Single-tier application — all capabilities reside in API/Backend execution context (specifically inside `tools/terminal/safety.py`).
</architectural_responsibility_map>

<research_summary>
## Summary

This research focuses on structural detection of shell chaining operators and escape-based command obfuscation. Because standard tokenizers like `shlex` do not treat operators like `;`, `&`, or `|` as delimiters when they are not space-separated, we cannot rely on token list matching alone. We propose a pre-tokenization quote-aware character scanner that flags unquoted operator symbols.

Furthermore, we address command obfuscation using carets, backslashes, or backticks inside words. We extend the token cleaning and obfuscation detection mechanism to strip these characters, blocking execution if the sanitized form matches a simple word/identifier and contains escape characters. Finally, variable expansions are blocked contextually at the command verb position (first token) or inside wrapper parameters to prevent execution-redirection while allowing benign parameter printing.

**Primary recommendation**: Implement a quote-aware character scanner on the raw command line for chaining, and extend token-level checks to handle escapes and contextual variable references.
</research_summary>

<standard_stack>
## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| re | Python stdlib | Pattern matching | Regex for variable pattern identification (`%VAR%`, `$VAR`, etc.). |
| shlex | Python stdlib | Command splitting | Token extraction after raw chaining checks. |
</standard_stack>

<architecture_patterns>
## Architecture Patterns

### Recommended Project Structure
This phase modifies/creates:
- [safety.py](file:///c:/Users/shrs/AgenticOS/tools/terminal/safety.py) - Adding quote-aware scanner and variable/escape checks.
- [test_terminal_safety_structural.py](file:///c:/Users/shrs/AgenticOS/tests/test_terminal_safety_structural.py) - Adding unit tests for chaining and obfuscation.

### Quote-Aware Scanner State Machine
```python
def check_chaining(command: str) -> bool:
    in_single = False
    in_double = False
    i = 0
    while i < len(command):
        char = command[i]
        if char == "'" and not in_double:
            in_single = not in_single
        elif char == '"' and not in_single:
            in_double = not in_double
        elif not in_single and not in_double:
            if char in {";", "|", "&", "`"}:
                return True
            if char == "$" and i + 1 < len(command) and command[i+1] == "(":
                return True
        i += 1
    return False
```
</architecture_patterns>

<dont_hand_roll>
## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Character escaping complexity | Custom character unescaping | Simple stripping + regex matches | Stripping all escapes and matching against `^[a-zA-Z0-9_-]+$` covers the malicious identifier obfuscation vector without needing a complete terminal shell parser. |
</dont_hand_roll>

<common_pitfalls>
## Common Pitfalls

### Pitfall 1: Space-less Operators
- **What goes wrong:** `echo hello;sc stop` is not split by `shlex` as separate tokens.
- **Why it happens:** Semicolon `;` is not a default token delimiter in `shlex`.
- **How to avoid:** Scan the raw command string character-by-character for unquoted operators before tokenization.

### Pitfall 2: Benign Paths with Backslashes
- **What goes wrong:** `C:\Windows\System32` is flagged as backslash obfuscation.
- **Why it happens:** Backslashes are treated as escapes on POSIX.
- **How to avoid:** Ensure the obfuscation check only flags escapes if the cleaned token (without quotes and escapes) is a simple word (`^[a-zA-Z0-9_-]+$`). File paths contain `:` or `\` or `.`, so they are naturally ignored.
</common_pitfalls>

<code_examples>
## Code Examples

### Caret and Backslash Sanitizer Heuristic
```python
def _clean_token_with_escapes(token: str) -> tuple[str, bool]:
    # 1. Clean quotes recursively using _clean_token
    # 2. Check for caret, backslash, backticks inside the cleaned token
    # 3. If present, strip them and verify if it matches an identifier pattern
    # ...
```
</code_examples>

<sota_updates>
## State of the Art (2026)
- Combining pre-split scanners with AST-like token validators provides defense-in-depth against shell execution bypasses.
</sota_updates>

<open_questions>
## Open Questions
None.
</open_questions>

<sources>
## Sources
- Empirical local test cases verified on Python 3.12.
</sources>

<metadata>
## Metadata
**Research scope:** Command chaining syntax, variable expansion formats, caret/backslash/backtick escapes.
**Confidence breakdown:** High confidence across standard stack and state machine behavior.
**Research date:** 2026-06-05
**Valid until:** 2026-07-05
</metadata>

---
*Phase: 02-shell-chaining-obfuscation-interception*
*Research completed: 2026-06-05*
*Ready for planning: yes*
