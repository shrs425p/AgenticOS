# Pitfalls Research

**Domain:** Agentic OS Control and Development Framework
**Researched:** 2026-06-26
**Confidence:** HIGH

## Critical Pitfalls

### Pitfall 1: Unicode Escape Bypass

**What goes wrong:** Attackers build executable command strings dynamically using PowerShell char casts (e.g. `$([char]0x73)c stop`).
**Why it happens:** Standard shell sanitizers check raw command strings for blacklisted verbs like `sc` but miss character cast expressions.
**How to avoid:** Run regex scan for hex/unicode escapes (`$([char]0xXX)`) before dispatching commands.
**Warning signs:** Command strings containing `$([char]`, `\u`, or `\x`.
**Phase to address:** Phase 1 (Security).

### Pitfall 2: Circular Dependency Reloads

**What goes wrong:** Modularizing `core/runtime.py` causes circular imports if files try to import each other's registry.
**Why it happens:** Tools import runtime to verify state; runtime imports tools to build the registry.
**How to avoid:** Define a clean interface/Protocol for tools and register them using dependency injection.
**Warning signs:** `ImportError: cannot import name ...` during tool discovery.
**Phase to address:** Phase 2 (Code Quality).

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Simple regex validation | Quick implementation | Bypassed by clever obfuscations | Never for security critical components |
| Buffering full tool logs | Simple stdout return | Memory leaks on long-running commands | Subprocess output under 500 lines |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Wayland screenshots | Using `gnome-screenshot` or standard X11 tool | Check environment session type and use `grim` |
| macOS windows | Querying raw desktop coordinates | Use AppleScript via accessibility System Events API |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| N+1 SQLite queries | Slow retrieval on large histories | Load all needed records in a single query | 1000+ interactions |
| Linear tool scan | 500ms delay before model responses | Index tool descriptions using vector similarity | 100+ tools |

---
*Pitfalls research for: AgenticOS*
*Researched: 2026-06-26*
