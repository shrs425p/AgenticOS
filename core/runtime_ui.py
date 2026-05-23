"""UI helpers and response parsing for the AgenticOs runtime."""

import sys
import time
import threading
import itertools
import re
import os
from typing import Optional
from core.logger import get_logger
logger = get_logger(__name__)

if sys.platform == "win32":
    # Enable VT100 Escape Sequence for WINDOWS 10+
    os.system("")





class Spinner:
    def __init__(self, message=None, delay=0.08, cfg: dict = None):
        self.cfg = cfg or {}
        prompts = self.cfg.get("prompts", {})
        ui_labels = prompts.get("ui_labels", {})
        
        self.message = message or ui_labels.get("spinner_message", "Thinking")
        self.delay = delay
        self.spinner = itertools.cycle(["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"])
        self.running = False
        self.thread = None

    def _spin(self):
        while self.running:
            sys.stdout.write(
                f"\r{C.TEAL}{next(self.spinner)}{C.RESET} {C.SLATE}{self.message}...{C.RESET} "
            )
            sys.stdout.flush()
            time.sleep(self.delay)

    def __enter__(self):
        self.running = True
        self.thread = threading.Thread(target=self._spin, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.running = False
        if self.thread:
            self.thread.join(timeout=0.2)
        sys.stdout.write("\r" + " " * (len(self.message) + 10) + "\r")
        sys.stdout.flush()


def typewriter_print(text: str, delay: float = 0.002, color: str = ""):
    # Optimized for IDEs: Print all at once to prevent IPC flooding and lag
    """typewriter_print function."""
    sys.stdout.write(color + text + C.RESET + "\n")
    sys.stdout.flush()


def pulse_line(length: int = 60, char: str = "─"):
    """Animate a line with a breathing color effect."""
    colors = [C.SLATE, C.DIM + C.SLATE, C.TEAL, C.BOLD + C.TEAL, C.TEAL, C.DIM + C.SLATE, C.SLATE]
    for _ in range(1):
        for col in colors:
            sys.stdout.write(f"\r{col}{char * length}{C.RESET}")
            sys.stdout.flush()
            time.sleep(0.04)
    sys.stdout.write("\n")


class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    
    # Premium Light & Soft True-Color Palette
    TEAL = "\033[38;2;167;219;216m"     # Soft Pastel Sage/Teal
    SLATE = "\033[38;2;148;163;184m"    # Soft Light Slate Gray
    PURPLE = "\033[38;2;196;181;253m"   # Soft Pastel Lavender
    AMBER = "\033[38;2;253;230;138m"    # Soft Pale Amber/Peach
    EMERALD = "\033[38;2;167;243;208m"  # Soft Pastel Mint Green
    ROSE = "\033[38;2;254;205;211m"     # Soft Pastel Rose
    BLUE = "\033[38;2;186;230;253m"     # Soft Pastel Ice Blue
    WHITE = "\033[38;2;248;250;252m"    # Soft Light Off-White

    # Standard Fallback Aliases
    RED = ROSE
    GREEN = EMERALD
    YELLOW = AMBER
    BLUE_STD = BLUE
    MAGENTA = PURPLE
    CYAN = TEAL
    GRAY = SLATE

    @staticmethod
    def strip(text: str) -> str:
        """strip function."""
        return re.sub(r"\033\[[0-9;]*m", "", text)


def banner(cfg: dict = None):
    """banner function."""
    cfg = cfg or {}
    subtitle = cfg.get("prompts", {}).get("ui_labels", {}).get("banner_subtitle", "Autonomous CLI Agent  •  Ollama / Nvidia NIM  •  Session Memory")
    logger.info(
        f"""
  {C.TEAL}{C.BOLD}▲  A G E N T I C   O S{C.RESET}  {C.SLATE}•  Workspace Intelligence{C.RESET}
  {C.SLATE}──────────────────────────────────────────────────────────────────────{C.RESET}
  {C.SLATE}{subtitle}{C.RESET}
"""
    )


def parse_actions(text: str) -> list[tuple]:
    """Extract one or more actions from model output.

    Supported formats:
    - ACTION: tool | arg1 | arg2
    - ACTION: {"tool": "...", "args": {...}}
    - ACTION: tool(arg1, arg2)
    """
    import json

    # Strip thinking blocks
    text = re.sub(r"(?i)<think>.*?</think>", "", text, flags=re.DOTALL)
    text = re.sub(r"(?i)<think>.*", "", text, flags=re.DOTALL)

    # Find all "ACTION:" headers
    # We use a non-greedy match for the content until the next keyword or end of string.
    try:
        from core.runtime_config import load_config
        cfg = load_config()
    except Exception:
        cfg = {}

    heuristics = cfg.get("heuristics", {})
    keywords = cfg.get("parser", {}).get("keywords", [
        "OBJECTIVE:",
        "STATE:",
        "REASONING:",
        "THOUGHT:",
        "PLAN:",
        "ACTION:",
        "FINAL ANSWER:",
        "OBSERVATION:",
    ])
    pattern = r"(?:\*\*|__)?ACTION(?:\*\*|__)?[:\s]+(.*?)(?=" + "|".join(keywords) + r"|$)"
    matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)

    if not matches:
        return []

    # Enforce single ACTION per response to prevent CoV misparsing and batching issues.
    if len(matches) > 1:
        matches = matches[:1]

    actions = []

    def _extract_first_json_object(s: str) -> str:
        start = s.find("{")
        if start == -1:
            return ""
        depth = 0
        in_quotes = False
        quote_char = None
        escape = False
        for i in range(start, len(s)):
            ch = s[i]
            if escape:
                escape = False
                continue
            if ch == "\\":
                escape = True
                continue
            if ch in ('"', "'"):
                if not in_quotes:
                    in_quotes = True
                    quote_char = ch
                elif ch == quote_char:
                    in_quotes = False
                    quote_char = None
                continue
            if in_quotes:
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return s[start : i + 1]
        return ""

    for content in matches:
        content = content.strip()
        # Strip common fenced code blocks
        content = re.sub(r"^```(?:json)?\s*", "", content, flags=re.IGNORECASE)
        content = re.sub(r"\s*```$", "", content)
        content = content.strip()

        if not content or content.lower() in ("none", "null", "(none)", "no action"):
            continue

        looks_like_tool = ("{" in content or re.match(r"^\s*[A-Za-z_]\w*\s*\(", content))
        prose_threshold = int(heuristics.get("prose_vs_tool_threshold", 120))
        if not looks_like_tool and len(content) > prose_threshold:
            continue

        parsed = False

        # 1. JSON action format
        json_blob = _extract_first_json_object(content)
        if json_blob:
            try:
                obj = json.loads(json_blob, strict=False)
                if isinstance(obj, dict):
                    if "tool" in obj:
                        tool = str(obj.get("tool", "")).strip()
                        args = obj.get("args", {})
                        if tool:
                            actions.append((tool, args))
                            parsed = True
                    elif "args" in obj and isinstance(obj.get("args"), dict):
                        a = obj.get("args") or {}
                        if "path" in a and ("content" in a or "data" in a):
                            actions.append(("write_file", a))
                            parsed = True
            except Exception:
                # If json.loads fails but it looks like JSON, don't fall back to pipe-separator
                # which would mangle it.
                pass

        if parsed:
            continue

        # 2. Function-call action format
        m_call = re.match(r"^\s*([A-Za-z_]\w*)\s*\((.*)\)\s*$", content, flags=re.DOTALL)
        if m_call:
            tool = m_call.group(1).strip()
            inside = (m_call.group(2) or "").strip()

            def _split_commas(s: str) -> list[str]:
                parts = []
                cur = ""
                in_q = False
                qch = None
                escape = False
                for ch in s:
                    if escape:
                        cur += ch
                        escape = False
                        continue
                    if ch == "\\":
                        cur += ch
                        escape = True
                        continue
                    if ch in ('"', "'"):
                        if not in_q:
                            in_q = True
                            qch = ch
                        elif ch == qch:
                            in_q = False
                            qch = None
                        cur += ch
                        continue
                    if ch == "," and not in_q:
                        parts.append(cur.strip())
                        cur = ""
                    else:
                        cur += ch
                if cur.strip():
                    parts.append(cur.strip())
                return parts

            def _strip_quotes(v: str) -> str:
                v = v.strip()
                if len(v) >= 2 and ((v[0] == v[-1] == '"') or (v[0] == v[-1] == "'")):
                    return v[1:-1]
                return v

            items = _split_commas(inside)
            if any("=" in it for it in items):
                kwargs = {}
                for it in items:
                    if "=" not in it:
                        continue
                    k, v = it.split("=", 1)
                    kwargs[k.strip()] = _strip_quotes(v)
                actions.append((tool, kwargs))
            else:
                args = [_strip_quotes(it) for it in items if it]
                actions.append((tool, args))
            continue

        # 3. Legacy Pipe-Separated (Only if it doesn't look like JSON)
        if not content.startswith("{"):
            parts = []
            cur = ""
            in_q = False
            qch = None
            for char in content:
                if char in ('"', "'"):
                    if not in_q:
                        in_q = True
                        qch = char
                    elif char == qch:
                        in_q = False
                        qch = None
                    cur += char
                elif char == "|" and not in_q:
                    parts.append(cur)
                    cur = ""
                else:
                    cur += char
            if cur:
                parts.append(cur)

            if parts:
                tool = parts[0].strip().strip("*_").strip()
                if tool.upper().startswith("ACTION:"):
                    tool = tool[7:].strip().strip("*_").strip()
                # Reject tool names that contain spaces or quotes — those are prose, not tool names
                if tool and re.match(r'^[A-Za-z_]\w*$', tool):
                    args = [arg if "\n" in arg else arg.strip() for arg in parts[1:]]
                    actions.append((tool, args))


    return actions


def parse_action(text: str) -> Optional[tuple]:
    """Deprecated: use parse_actions instead. Returns the first action found."""
    actions = parse_actions(text)
    return actions[0] if actions else None


def has_final_answer(text: str) -> bool:
    """has_final_answer function."""
    return "FINAL ANSWER:" in text.upper()


def print_section(label: str, content: str, color: str = C.TEAL, max_len: int = 1000):
    """print_section function."""
    logger.info(f"\n{color}{C.BOLD}❯ {label}{C.RESET}")
    if content:
        typewriter_print(
            content[:max_len] if len(content) > max_len else content, color=C.SLATE
        )


def print_action(tool: str, args, symbol: str = "❯"):
    """print_action function."""
    if isinstance(args, dict):
        arg_str = ", ".join(f"{C.SLATE}{k}={C.RESET}{v}" for k, v in args.items())
    else:
        arg_str = ", ".join(str(a) for a in (args or []))
    logger.info(
        f"\n{C.SLATE}❯ {C.EMERALD}call: {C.WHITE}{tool}{C.RESET}({arg_str})"
    )


def print_observation(result: str, max_len: int = 600):
    """print_observation function."""
    preview = (
        result
        if len(result) < max_len
        else result[:max_len] + f"\n{C.SLATE}... (truncated){C.RESET}"
    )
    
    # Blockquote formatting with vertical slate lines
    lines = preview.splitlines()
    formatted_lines = [f"{C.SLATE}│{C.RESET} {line}" for line in lines]
    formatted_text = "\n".join(formatted_lines)
    
    logger.info(f"{C.SLATE}❯ {C.PURPLE}obs:{C.RESET}")
    sys.stdout.write(C.SLATE + formatted_text + C.RESET + "\n")
    sys.stdout.flush()


def print_error(msg: str):
    """print_error function."""
    logger.info(f"\n{C.ROSE}✗ {msg}{C.RESET}")


def print_warning(msg: str):
    """print_warning function."""
    logger.info(f"\n{C.AMBER}▲ {msg}{C.RESET}")


def print_info(msg: str):
    """print_info function."""
    logger.info(f"{C.BLUE}◆ {C.SLATE}{msg}{C.RESET}")


def print_success(msg: str):
    """print_success function."""
    logger.info(f"{C.EMERALD}✓ {msg}{C.RESET}")
