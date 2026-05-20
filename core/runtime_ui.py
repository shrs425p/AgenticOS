
"""UI helpers and response parsing for the AgenticOs runtime."""

import sys
import time
import threading
import itertools
import re
from typing import Optional
from core.logger import get_logger
logger = get_logger(__name__)





class Spinner:
    def __init__(self, message=None, delay=0.1, cfg: dict = None):
        self.cfg = cfg or {}
        prompts = self.cfg.get("prompts", {})
        ui_labels = prompts.get("ui_labels", {})
        
        self.message = message or ui_labels.get("spinner_message", "Thinking")
        self.delay = delay
        self.spinner = itertools.cycle(["|", "/", "-", "\\"])
        self.running = False
        self.thread = None

    def _spin(self):
        while self.running:
            sys.stdout.write(
                f"\r{C.CYAN}{next(self.spinner)}{C.RESET} {C.DIM}{self.message}...{C.RESET} "
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
    sys.stdout.write(color + text + C.RESET + "\n")
    sys.stdout.flush()


def pulse_line(length: int = 60, char: str = "="):
    """Animate a line with a breathing color effect."""
    colors = [C.GRAY, C.DIM, C.CYAN, C.BOLD + C.CYAN, C.CYAN, C.DIM, C.GRAY]
    for _ in range(2):
        for col in colors:
            sys.stdout.write(f"\r{col}{char * length}{C.RESET}")
            sys.stdout.flush()
            time.sleep(0.05)
    sys.stdout.write("\n")


class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    GRAY = "\033[90m"

    @staticmethod
    def strip(text: str) -> str:

        return re.sub(r"\033\[[0-9;]*m", "", text)


def banner(cfg: dict = None):
    cfg = cfg or {}
    subtitle = cfg.get("prompts", {}).get("ui_labels", {}).get("banner_subtitle", "Autonomous CLI Agent  •  Ollama / Nvidia NIM  •  Session Memory")
    logger.info(
        f"""
{C.CYAN}{C.BOLD}
  █████╗  ██████╗ ███████╗███╗   ██╗████████╗██╗ ██████╗  ██████╗ ███████╗
 ██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝██║██╔════╝ ██╔═══██╗██╔════╝
 ███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║   ██║██║      ██║   ██║███████╗
 ██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║   ██║██║      ██║   ██║╚════██║
 ██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║   ██║╚██████╗ ╚██████╔╝███████║
 ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝   ╚═╝ ╚═════╝  ╚═════╝ ╚══════╝
{C.RESET}{C.GRAY}  {subtitle}
{C.RESET}"""
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
                obj = json.loads(json_blob)
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
    return "FINAL ANSWER:" in text.upper()


def print_section(label: str, content: str, color: str = C.CYAN, max_len: int = 1000):
    logger.info(f"\n{color}{C.BOLD}-- {label} {'-' * (50 - len(label))}{C.RESET}")
    if content:
        typewriter_print(
            content[:max_len] if len(content) > max_len else content, color=C.DIM
        )


def print_action(tool: str, args, symbol: str = "[*]"):
    if isinstance(args, dict):
        arg_str = " | ".join(f"{k}={v}" for k, v in args.items())
    else:
        arg_str = " | ".join(str(a) for a in (args or []))
    logger.info(
        f"\n{C.YELLOW}{C.BOLD}{symbol}  ACTION:{C.RESET} {C.YELLOW}{tool}{C.RESET} {C.DIM}< {arg_str} >{C.RESET}"
    )


def print_observation(result: str, max_len: int = 600):
    preview = (
        result
        if len(result) < max_len
        else result[:max_len] + f"\n{C.GRAY}... (truncated){C.RESET}"
    )
    logger.info(f"{C.MAGENTA}{C.BOLD}OBSERVATION:{C.RESET}")
    typewriter_print(preview, color=C.GRAY, delay=0.001)


def print_error(msg: str):
    logger.info(f"\n{C.RED}{C.BOLD}ERROR:{C.RESET} {C.RED}{msg}{C.RESET}")


def print_warning(msg: str):
    logger.info(f"\n{C.YELLOW}{C.BOLD}WARNING:{C.RESET} {C.YELLOW}{msg}{C.RESET}")


def print_info(msg: str):
    logger.info(f"{C.BLUE}INFO: {msg}{C.RESET}")




def print_success(msg: str):
    logger.info(f"{C.GREEN}OK: {msg}{C.RESET}")
