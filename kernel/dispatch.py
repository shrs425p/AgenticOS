"""Action verification and dispatching logic for the AgenticOs runtime."""

import re
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Tuple, Any, Callable, Optional, AsyncIterator

# ---------------------------------------------------------------------------
# Existing: verify_action
# ---------------------------------------------------------------------------

def verify_action(agent, tool_name: str, args: Dict, context: str) -> Tuple[bool, str]:
    """
    Performs a 'mental simulation' to verify if the tool call is valid and necessary.
    """
    # Hard Check: Tool Existence
    if tool_name not in agent.ops.registry:
        return (
            False,
            f"Tool '{tool_name}' is not in the registry. Check /ops for available capabilities.",
        )

    # Soft Check: Model Verification
    verification_cfg = agent.cfg.get("prompts", {}).get("verification", {})
    prompt_tmpl = verification_cfg.get("prompt", "").strip()
    if not prompt_tmpl:
        prompt_tmpl = (
            "You are the Technical Verification Monitor for AgenticOs.\n"
            "Your ONLY job is to verify the technical validity and safety of the proposed action.\n\n"
            "TOOL: {tool_name}\n"
            "ARGS: {args}\n\n"
            "CONTEXT (Recent history):\n"
            "{context}\n\n"
            "STRICT VERIFICATION RULES:\n"
            "1. TECHNICAL VALIDITY: Are the arguments logically sound? (e.g. if reading a file, has it been identified/created?)\n"
            "2. ANTI-LOOP: Is the agent repeating the EXACT same command that just failed or yielded no new info?\n"
            "3. NO STRATEGY JUDGMENT: Do NOT reject an action because it is 'insufficient' to solve the whole task. "
            "Tasks are solved via MANY small, sequential steps. Sequential searches are VALID.\n"
            "4. TOOL EXISTENCE: Assume the tool '{tool_name}' is valid and registered. Do NOT reject based on tool name existence.\n\n"
            "REPLY FORMAT:\n"
            "If the action is technically valid, reply ONLY with 'OK'.\n"
            "If invalid, broken, or a loop, reply 'REJECT: [concise technical reason]'"
        )

    prompt = prompt_tmpl.format(tool_name=tool_name, args=args, context=context)

    try:
        # Use cov_model if specified, otherwise use active model
        original_model = agent.client.model
        if agent.cov_model:
            agent.client.model = agent.cov_model

        # Use a minimal message history for speed
        verification_msgs = [{"role": "user", "content": prompt}]
        system_msg = verification_cfg.get(
            "system", "You are a strict verification monitor."
        )
        response = agent.client.chat(verification_msgs, system=system_msg)

        if agent.cov_model:
            agent.client.model = original_model

        response = response.strip()
        if response.upper() == "OK":
            return True, "OK"
        elif response.upper().startswith("REJECT:"):
            return False, response[7:].strip()
        else:
            # Ambiguous response, default to OK but log it
            return True, "OK"
    except Exception as e:
        return True, f"Verification skipped due to error: {e}"


# ---------------------------------------------------------------------------
# Task 02-02-01: StreamingActionParser
# ---------------------------------------------------------------------------

# Keywords that terminate an ACTION: block (same set used by parse_actions())
_TERMINATOR_KEYWORDS = [
    "OBSERVATION:",
    "FINAL ANSWER:",
    "OBJECTIVE:",
    "TASK:",
    "PLAN:",
    "ACTION:",
    "STATE:",
    "REASONING:",
    "THOUGHT:",
]

# Regex pattern: ACTION: block terminated by known keywords OR end-of-string.
# We compile once at module level for performance.
_ACTION_PATTERN = re.compile(
    r"(?:\*\*|__)?ACTION(?:\*\*|__)?[:\s]+(.*?)(?="
    + "|".join(re.escape(kw) for kw in _TERMINATOR_KEYWORDS)
    + r"|$)",
    re.IGNORECASE | re.DOTALL,
)


def _extract_first_json_object(s: str) -> str:
    """Return the first balanced JSON object substring found in *s*."""
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


def _parse_action_content(content: str) -> Optional[Tuple[str, dict]]:
    """Parse a single ACTION content string into a (tool_name, args) tuple.

    Returns None if the content cannot be parsed into a valid action.
    Uses the same JSON-first approach as parse_actions() in runtime_ui.py.
    """
    content = content.strip()

    # Strip fenced code blocks
    content = re.sub(r"^```(?:json)?\s*", "", content, flags=re.IGNORECASE)
    content = re.sub(r"\s*```$", "", content)
    content = content.strip()

    if not content or content.lower() in ("none", "null", "(none)", "no action"):
        return None

    # 1. JSON object format: {"tool": "...", "args": {...}}
    json_blob = _extract_first_json_object(content)
    if json_blob:
        try:
            obj = json.loads(json_blob, strict=False)
            if isinstance(obj, dict) and "tool" in obj:
                tool = str(obj.get("tool", "")).strip()
                args = obj.get("args", {})
                if tool:
                    return (tool, args if isinstance(args, dict) else {})
        except Exception:
            pass

    return None


class StreamingActionParser:
    """Incrementally parse ACTION: blocks from streaming LLM output chunks.

    Usage::

        parser = StreamingActionParser()
        for chunk in stream:
            actions = parser.feed(chunk)
            for tool_name, args in actions:
                handle_action(tool_name, args)
        # After stream ends, flush any remaining partial action
        for tool_name, args in parser.flush():
            handle_action(tool_name, args)
    """

    def __init__(self):
        self._buf = ""

    def feed(self, chunk: str) -> list:
        """Feed a streaming chunk; returns fully-parsed actions if any complete ACTION: block found.

        A block is considered *complete* when it is followed by another known keyword
        (e.g. OBSERVATION:, FINAL ANSWER:) or when the buffer ends with a closing ``}``
        after a valid JSON object.

        Returns:
            list[tuple[str, dict]]: Zero or more ``(tool_name, args)`` tuples.
        """
        self._buf += chunk
        return self._extract_actions()

    def _extract_actions(self) -> list:
        """Scan the buffer for complete ACTION: blocks and parse them.

        A block is *complete* when it is terminated by another keyword in the buffer
        (not just end-of-string). Blocks at the very end of the buffer (i.e. terminated
        only by ``$``) are NOT extracted here — they are held back until :meth:`flush`
        or until a subsequent :meth:`feed` call provides a terminator.

        However, if the trailing block ends with a ``}`` that closes a valid JSON object
        we treat it as complete and extract it immediately.
        """
        results = []

        # Find all ACTION: occurrences and their content spans.
        # We look for blocks that are terminated by a keyword (not just $).
        keyword_terminated_pattern = re.compile(
            r"(?:\*\*|__)?ACTION(?:\*\*|__)?[:\s]+(.*?)(?="
            + "|".join(re.escape(kw) for kw in _TERMINATOR_KEYWORDS)
            + r")",
            re.IGNORECASE | re.DOTALL,
        )

        for m in keyword_terminated_pattern.finditer(self._buf):
            content = m.group(1)
            parsed = _parse_action_content(content)
            if parsed:
                results.append(parsed)

        # Also check: is there a trailing (unterminated) ACTION block whose content
        # ends with a closing JSON brace (i.e. the JSON object is complete)?
        tail_pattern = re.compile(
            r"(?:\*\*|__)?ACTION(?:\*\*|__)?[:\s]+(.*?)$",
            re.IGNORECASE | re.DOTALL,
        )
        # Only examine the last ACTION: occurrence in the buffer.
        tail_matches = list(tail_pattern.finditer(self._buf))
        if tail_matches:
            last_m = tail_matches[-1]
            content = last_m.group(1).strip()
            # Check if content already extracted by keyword-terminated pattern
            already_extracted = any(
                m.start() == last_m.start()
                for m in keyword_terminated_pattern.finditer(self._buf)
            )
            if not already_extracted and content.endswith("}"):
                parsed = _parse_action_content(content)
                if parsed:
                    results.append(parsed)

        # Remove extracted content from buffer to avoid double-parsing.
        # We rebuild the buffer keeping only the un-parsed tail.
        if results:
            # Find the end of the last consumed ACTION block.
            # Strategy: remove everything up to and including the last keyword match,
            # or clear if we consumed the tail.
            all_kw_matches = list(keyword_terminated_pattern.finditer(self._buf))
            if all_kw_matches:
                # The buffer after the last keyword-terminated match starts at the
                # position of the next keyword (the terminator).
                last_kw_end = all_kw_matches[-1].end()
                self._buf = self._buf[last_kw_end:]

            # If we consumed a tail block (ended with }), clear the buffer.
            tail_matches_after = list(
                keyword_terminated_pattern.finditer(self._buf)
            )
            if not tail_matches_after and results:
                # Check whether any result came from a tail (buffer ends with })
                tail_check = list(tail_pattern.finditer(self._buf))
                if tail_check:
                    tc = tail_check[-1]
                    content = tc.group(1).strip()
                    if content.endswith("}"):
                        parsed = _parse_action_content(content)
                        if parsed and parsed in results:
                            self._buf = ""

        return results

    def flush(self) -> list:
        """Parse any remaining content in the buffer, regardless of terminator.

        Call this after the stream ends to capture any action that wasn't followed
        by a keyword terminator.

        Returns:
            list[tuple[str, dict]]: Zero or more ``(tool_name, args)`` tuples.
        """
        results = []
        tail_pattern = re.compile(
            r"(?:\*\*|__)?ACTION(?:\*\*|__)?[:\s]+(.*?)$",
            re.IGNORECASE | re.DOTALL,
        )
        for m in tail_pattern.finditer(self._buf):
            parsed = _parse_action_content(m.group(1))
            if parsed:
                results.append(parsed)

        self._buf = ""
        return results

    def reset(self):
        """Clear internal buffer state."""
        self._buf = ""


# ---------------------------------------------------------------------------
# Task 02-02-02: ParallelScheduler & execute_actions_parallel
# ---------------------------------------------------------------------------


class ParallelScheduler:
    """Resolves dependency graphs for batched actions and executes independent ones concurrently.

    Each action descriptor is a dict with:
      - ``'tool'``: str — the tool name.
      - ``'args'``: dict — the tool arguments.
      - ``'depends_on'``: list[int] (optional) — indices of actions this action depends on.

    Actions without ``depends_on`` (or with an empty list) are considered independent
    and may be executed concurrently with other actions in the same *wave*.

    Waves are computed via Kahn's topological sort algorithm.  All actions in a wave
    are submitted to a :class:`~concurrent.futures.ThreadPoolExecutor` simultaneously.
    """

    def __init__(self, max_workers: Optional[int] = None):
        if max_workers is None:
            try:
                from kernel.resources import profile_hardware
                max_workers = profile_hardware().recommended_max_workers
            except Exception:
                max_workers = 4
        self.max_workers = max_workers

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def _is_async_tool(self, tool: str, executor_fn: Callable) -> bool:
        """Check if the tool is registered as an async tool."""
        if hasattr(executor_fn, "__self__") and hasattr(executor_fn.__self__, "registry"):
            registry = executor_fn.__self__.registry
            if tool in registry:
                fn = registry[tool]["fn"]
                return getattr(fn, "_is_async", False) or asyncio.iscoroutinefunction(fn)
        if asyncio.iscoroutinefunction(executor_fn):
            return True
        if "async" in tool.lower():
            return True
        return False

    def execute(
        self,
        actions: List[Dict],
        executor_fn: Callable[[str, dict], str],
    ) -> List[str]:
        """Execute *actions* respecting dependencies, running independent actions concurrently.

        Args:
            actions: List of action descriptor dicts.
            executor_fn: Callable that takes ``(tool_name, args)`` and returns an
                         observation string.

        Returns:
            List of observation strings in the original action order.
        """
        if not actions:
            return []

        results: List[Optional[str]] = [None] * len(actions)
        waves = self._build_waves(actions)

        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            for wave in waves:
                # Group actions in this wave into sync and async
                async_actions = []
                sync_actions = []
                for idx in wave:
                    action = actions[idx]
                    tool = action.get("tool", "")
                    if self._is_async_tool(tool, executor_fn):
                        async_actions.append(idx)
                    else:
                        sync_actions.append(idx)

                futures = {}
                # Submit sync actions to thread pool
                for idx in sync_actions:
                    action = actions[idx]
                    tool = action.get("tool", "")
                    args = action.get("args", {})
                    future = pool.submit(self._safe_call, executor_fn, tool, args)
                    futures[future] = idx

                # Run async actions concurrently in an event loop using asyncio.gather
                if async_actions:
                    async def run_async_actions():
                        coros = []
                        for idx in async_actions:
                            action = actions[idx]
                            tool = action.get("tool", "")
                            args = action.get("args", {})
                            
                            async def wrap_coro(t, a):
                                try:
                                    res = executor_fn(t, a)
                                    if asyncio.iscoroutine(res):
                                        return await res
                                    return res
                                except Exception as exc:
                                    return f"Error executing '{t}': {type(exc).__name__}: {exc}"
                                    
                            coros.append(wrap_coro(tool, args))
                        return await asyncio.gather(*coros)

                    def run_in_loop():
                        try:
                            return asyncio.run(run_async_actions())
                        except RuntimeError:
                            # Loop is already running, use a new loop
                            loop = asyncio.new_event_loop()
                            try:
                                return loop.run_until_complete(run_async_actions())
                            finally:
                                loop.close()

                    async_future = pool.submit(run_in_loop)
                    try:
                        async_results = async_future.result()
                        for idx, val in zip(async_actions, async_results):
                            results[idx] = val
                    except Exception as e:
                        for idx in async_actions:
                            action = actions[idx]
                            tool = action.get("tool", "")
                            results[idx] = f"Error executing async ops: {e}"

                # Gather sync action results
                for future in as_completed(futures):
                    idx = futures[future]
                    results[idx] = future.result()

        return [r if r is not None else "" for r in results]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _safe_call(
        executor_fn: Callable[[str, dict], str],
        tool: str,
        args: dict,
    ) -> str:
        """Wrap executor_fn so exceptions are captured as observation strings."""
        try:
            res = executor_fn(tool, args)
            if asyncio.iscoroutine(res):
                try:
                    return asyncio.run(res)
                except RuntimeError:
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor(1) as executor:
                        return executor.submit(asyncio.run, res).result()
            return res
        except Exception as exc:  # noqa: BLE001
            return f"Error executing '{tool}': {type(exc).__name__}: {exc}"

    def _build_waves(self, actions: List[Dict]) -> List[List[int]]:
        """Group action indices into ordered waves using Kahn's algorithm.

        Actions within the same wave have no dependency on each other and can
        execute concurrently.  Waves must be executed sequentially (wave N+1
        only starts after wave N completes).

        Returns:
            List of waves; each wave is a list of action indices.

        Raises:
            ValueError: If a cyclic dependency is detected.
        """
        n = len(actions)
        # Build adjacency: deps[i] = set of indices that i depends on
        deps: List[set] = [set() for _ in range(n)]
        # reverse_deps[i] = set of indices that depend on i
        reverse_deps: List[set] = [set() for _ in range(n)]

        for i, action in enumerate(actions):
            for dep_idx in action.get("depends_on", []) or []:
                if 0 <= dep_idx < n and dep_idx != i:
                    deps[i].add(dep_idx)
                    reverse_deps[dep_idx].add(i)

        # Kahn's algorithm
        in_degree = [len(deps[i]) for i in range(n)]
        ready = [i for i in range(n) if in_degree[i] == 0]

        waves: List[List[int]] = []
        processed = 0

        while ready:
            wave = sorted(ready)  # deterministic order
            waves.append(wave)
            processed += len(wave)
            next_ready = []
            for idx in wave:
                for dependent in reverse_deps[idx]:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        next_ready.append(dependent)
            ready = next_ready

        if processed != n:
            raise ValueError(
                f"Cyclic dependency detected in action graph "
                f"(processed {processed}/{n} actions)."
            )

        return waves


def execute_actions_parallel(
    actions: List[Tuple[str, Dict]],
    executor_fn: Callable[[str, Dict], str],
    max_workers: Optional[int] = None,
    enabled: bool = True,
) -> List[str]:
    """Execute a list of ``(tool_name, args)`` tuples, running independent ones in parallel.

    Args:
        actions: Sequence of ``(tool_name, args)`` pairs to execute.
        executor_fn: Callable ``(tool_name, args) -> observation_str``.
        max_workers: Maximum number of parallel workers.
        enabled: If ``False``, falls back to sequential execution regardless of count.

    Returns:
        List of observation strings in the original action order.
    """
    if not enabled or len(actions) <= 1:
        return [executor_fn(t, a) for t, a in actions]

    # All actions are independent by default (no depends_on)
    action_dicts = [{"tool": t, "args": a} for t, a in actions]
    scheduler = ParallelScheduler(max_workers=max_workers)
    return scheduler.execute(action_dicts, executor_fn)


def pipe_ops(tool_a: Any, toolb: Any) -> Any:
    """Composer to chain two ops together.
    
    The outputs of tool_a (either streamed or called) are fed as inputs to toolb.
    If tool_a is a streaming tool, we accumulate its stream and pass it to toolb.
    If toolb has a stream method, the piped tool also supports streaming.
    """
    class PipedTool:
        def __init__(self, ta: Any, tb: Any):
            self.tool_a = ta
            self.toolb = tb
            self._is_tool = True
            self._is_async = True
            
            # Retrieve names
            a_name = getattr(ta, "_tool_name", getattr(ta, "__name__", "tool_a"))
            b_name = getattr(tb, "_tool_name", getattr(tb, "__name__", "toolb"))
            self._tool_name = f"piped_{a_name}_{b_name}"
            
            a_desc = getattr(ta, "_tool_desc", "tool_a")
            b_desc = getattr(tb, "_tool_desc", "toolb")
            self._tool_desc = f"Piped: {a_desc} -> {b_desc}"
            
            # Setup metadata if possible
            try:
                from kernel.base import ToolMetadata
                self.metadata = ToolMetadata(
                    name=self._tool_name,
                    description=self._tool_desc,
                    category="Composite",
                    version="1.0.0",
                    author="AgenticOS"
                )
            except Exception:
                self.metadata = None

        async def __call__(self, *args: Any, **kwargs: Any) -> Any:
            # 1. Execute tool_a and get output
            if hasattr(self.tool_a, "stream"):
                chunks = []
                async for chunk in self.tool_a.stream(*args, **kwargs):
                    chunks.append(chunk)
                input_val = "".join(chunks)
            else:
                if asyncio.iscoroutinefunction(self.tool_a) or getattr(self.tool_a, "_is_async", False) or (callable(getattr(self.tool_a, "__call__", None)) and (asyncio.iscoroutinefunction(self.tool_a.__call__) or getattr(self.tool_a.__call__, "_is_async", False))):
                    input_val = await self.tool_a(*args, **kwargs)
                else:
                    input_val = self.tool_a(*args, **kwargs)

            # 2. Feed input_val into toolb
            if asyncio.iscoroutinefunction(self.toolb) or getattr(self.toolb, "_is_async", False) or (callable(getattr(self.toolb, "__call__", None)) and (asyncio.iscoroutinefunction(self.toolb.__call__) or getattr(self.toolb.__call__, "_is_async", False))):
                return await self.toolb(input_val)
            else:
                return self.toolb(input_val)

        async def stream(self, *args: Any, **kwargs: Any) -> AsyncIterator[str]:
            # If toolb supports streaming, we stream toolb's output
            # Otherwise we stream tool_a's output, then pass it to toolb and yield the final result
            if hasattr(self.tool_a, "stream"):
                chunks = []
                async for chunk in self.tool_a.stream(*args, **kwargs):
                    chunks.append(chunk)
                input_val = "".join(chunks)
            else:
                if asyncio.iscoroutinefunction(self.tool_a) or getattr(self.tool_a, "_is_async", False) or (callable(getattr(self.tool_a, "__call__", None)) and (asyncio.iscoroutinefunction(self.tool_a.__call__) or getattr(self.tool_a.__call__, "_is_async", False))):
                    input_val = await self.tool_a(*args, **kwargs)
                else:
                    input_val = self.tool_a(*args, **kwargs)

            if hasattr(self.toolb, "stream"):
                async for chunk in self.toolb.stream(input_val):
                    yield chunk
            else:
                if asyncio.iscoroutinefunction(self.toolb) or getattr(self.toolb, "_is_async", False) or (callable(getattr(self.toolb, "__call__", None)) and (asyncio.iscoroutinefunction(self.toolb.__call__) or getattr(self.toolb.__call__, "_is_async", False))):
                    res = await self.toolb(input_val)
                else:
                    res = self.toolb(input_val)
                yield str(res)

    return PipedTool(tool_a, toolb)
