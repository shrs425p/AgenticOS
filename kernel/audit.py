"""Structured audit logging (no chat content).

Writes separate JSONL logs for:
- session events (start/stop, provider/model)
- tool calls (timing, args summary, validation, success)
- errors
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime


def _now_iso() -> str:
    return datetime.now().isoformat(sep=" ", timespec="seconds")


def _safe_mkdir(path: str):
    try:
        os.makedirs(path, exist_ok=True)
    except Exception:
        pass


def _redact(text: str, patterns: list = None, cfg: dict = None) -> str:
    if not text:
        return ""
    s = str(text)
    if patterns is None:
        if cfg:
            patterns = cfg.get("policy", {}).get("redaction_patterns")
        
        if not patterns:
            # Absolute fallback if cfg is missing
            patterns = [
                (r"(?i)(NVIDIA_API_KEY\s*=\s*)([^\s]+)", r"\1[REDACTED]"),
                (r"(?i)(OPENAI_API_KEY\s*=\s*)([^\s]+)", r"\1[REDACTED]"),
                (r"(?i)(Authorization:\s*Bearer\s+)([A-Za-z0-9._-]+)", r"\1[REDACTED]"),
                (r"(?i)(Bearer\s+)([A-Za-z0-9._-]{12,})", r"\1[REDACTED]"),
                (r"(?i)(nvapi-[A-Za-z0-9_-]{8,})", "[REDACTED]"),
            ]
    
    for pat_item in patterns:
        try:
            if isinstance(pat_item, (list, tuple)) and len(pat_item) == 2:
                pat, repl = pat_item
            else:
                continue
            s = re.sub(pat, repl, s)
        except Exception:
            continue
    return s


def _estimate_tokens(text: str) -> int:
    """Cheap token estimate used for telemetry (no provider usage required)."""
    s = str(text or "")
    return max(1, int(len(s) / 4))


@dataclass
class AuditLogger:
    log_dir: str
    enabled: bool = True
    fmt: str = "jsonl"  # jsonl | log | both
    cfg: dict = None

    def __post_init__(self):
        self.cfg = self.cfg or {}
        self.log_cfg = self.cfg.get("logging", {})
        names = self.log_cfg.get("filenames", {})
        _safe_mkdir(self.log_dir)
        
        s_name = names.get("session", "session")
        t_name = names.get("ops", "ops")
        e_name = names.get("errors", "errors")
        p_name = names.get("paths", "paths")

        self.session_log = os.path.join(self.log_dir, f"{s_name}.jsonl")
        self.ops_log = os.path.join(self.log_dir, f"{t_name}.jsonl")
        self.errors_log = os.path.join(self.log_dir, f"{e_name}.jsonl")
        self.paths_log = os.path.join(self.log_dir, f"{p_name}.jsonl")
        self.session_text = os.path.join(self.log_dir, f"{s_name}.log")
        self.ops_text = os.path.join(self.log_dir, f"{t_name}.log")
        self.errors_text = os.path.join(self.log_dir, f"{e_name}.log")
        self.paths_text = os.path.join(self.log_dir, f"{p_name}.log")
        self._seen_paths: set[str] = set()

    def _writejsonl(self, path: str, obj: dict):
        if not self.enabled:
            return
        if self.fmt not in ("jsonl", "both"):
            return
        try:
            with open(path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(obj, ensure_ascii=False) + "\n")
        except Exception:
            pass

    def _write_log(self, path: str, line: str):
        if not self.enabled:
            return
        if self.fmt not in ("log", "both"):
            return
        try:
            with open(path, "a", encoding="utf-8") as handle:
                handle.write(line.rstrip() + "\n")
        except Exception:
            pass

    def session_start(self, session_id: str, provider: str, model: str, workspace: str):
        """session_start function."""
        obj = {
            "ts": _now_iso(),
            "event": "session_start",
            "session_id": session_id,
            "provider": provider,
            "model": model,
            "workspace": workspace,
        }
        self._writejsonl(self.session_log, obj)
        self._write_log(
            self.session_text,
            f"{obj['ts']} session_start session_id={session_id} provider={provider} model={model} workspace={workspace}",
        )
        # Record per-session metadata for quick grep.
        self._write_log(
            self.paths_text,
            f"{obj['ts']} session_meta session_id={session_id} provider={provider} model={model}",
        )

    def session_end(self, session_id: str, status: str = "ended"):
        """session_end function."""
        obj = {
            "ts": _now_iso(),
            "event": "session_end",
            "session_id": session_id,
            "status": status,
        }
        self._writejsonl(self.session_log, obj)
        self._write_log(
            self.session_text,
            f"{obj['ts']} session_end session_id={session_id} status={status}",
        )

    def tool_call(
        self,
        session_id: str,
        tool_name: str,
        tool_args: str,
        started_ts: float,
        ended_ts: float,
        success: bool,
        validation: str = "",
        observation_preview: str = "",
    ):
        """tool_call function."""
        dur_ms = int(max(0.0, (ended_ts - started_ts) * 1000))
        args_limit = int(self.log_cfg.get("args_truncation_limit", 2000))
        val_limit = int(self.log_cfg.get("validation_truncation_limit", 500))
        obs_limit = int(self.log_cfg.get("observation_truncation_limit", 800))
        
        args_preview = _redact(tool_args, cfg=self.cfg)[:args_limit]
        val_preview = (validation or "")[:val_limit]
        obs_preview = _redact(observation_preview or "", cfg=self.cfg)[:obs_limit]
        obj = {
            "ts": _now_iso(),
            "event": "tool_call",
            "session_id": session_id,
            "tool": tool_name,
            "args": args_preview,
            "duration_ms": dur_ms,
            "success": bool(success),
            "validation": val_preview,
            "observation_preview": obs_preview,
        }
        self._writejsonl(self.ops_log, obj)

        # Keep .log compact and scan-friendly (single-line).
        flat_args = args_preview.replace("\r", " ").replace("\n", " ")
        flat_obs = obs_preview.replace("\r", " ").replace("\n", " ")
        flat_val = val_preview.replace("\r", " ").replace("\n", " ")
        self._write_log(
            self.ops_text,
            f"{obj['ts']} tool_call session_id={session_id} tool={tool_name} success={bool(success)} duration_ms={dur_ms} args={flat_args!r} validation={flat_val!r} obs={flat_obs!r}",
        )
        # Also record any real filesystem paths encountered (separate paths.log).
        try:
            base = os.environ.get("AGENT_BASE_DIR", "").strip()
            ws = os.path.join(base, "workspace") if base else ""
            self.paths_from_event(
                session_id=session_id,
                tool=tool_name,
                tool_args=tool_args,
                observation=observation_preview,
                base_dir=base,
                workspace_dir=ws,
            )
        except Exception:
            pass

    def error(self, session_id: str, where: str, message: str):
        """error function."""
        error_limit = int(self.log_cfg.get("error_truncation_limit", 4000))
        msg = _redact(message, cfg=self.cfg)[:error_limit]
        obj = {
            "ts": _now_iso(),
            "event": "error",
            "session_id": session_id,
            "where": where,
            "message": msg,
        }
        self._writejsonl(self.errors_log, obj)
        flat = msg.replace("\r", " ").replace("\n", " ")
        self._write_log(
            self.errors_text,
            f"{obj['ts']} error session_id={session_id} where={where} message={flat!r}",
        )

    def path_seen(self, session_id: str, tool: str, path: str, kind: str = "path"):
        """Record an existing path that the agent touched/resolved.

        This intentionally does not log any chat content; only paths that exist on disk.
        """
        if not self.enabled:
            return
        p = (path or "").strip()
        if not p:
            return
        if p in self._seen_paths:
            return
        self._seen_paths.add(p)
        obj = {
            "ts": _now_iso(),
            "event": "path_seen",
            "session_id": session_id,
            "tool": tool,
            "kind": kind,
            "path": p,
        }
        self._writejsonl(self.paths_log, obj)
        self._write_log(
            self.paths_text,
            f"{obj['ts']} path_seen session_id={session_id} tool={tool} kind={kind} path={p}",
        )

    def paths_from_event(
        self,
        session_id: str,
        tool: str,
        tool_args: str,
        observation: str,
        base_dir: str = "",
        workspace_dir: str = "",
    ):
        """Extract existing filesystem paths from args/observation and log them.

        Heuristics:
        - Extract Windows absolute paths like C:\foo\bar.
        - Extract quoted/space-separated tokens that look like relative paths (e.g., report.md),
          then resolve them against workspace_dir and base_dir, and log only if they exist.
        """
        if not self.enabled:
            return
        import re

        texts = [tool_args or "", observation or ""]
        blob = "\n".join(texts)

        # 1) Windows absolute paths.
        abs_paths = set(re.findall(r"[A-Za-z]:\\\\[^\r\n\t\"'<>|]+", blob))
        for p in sorted(abs_paths):
            try:
                if os.path.exists(p):
                    self.path_seen(session_id, tool, p, kind="absolute")
            except Exception:
                continue

        # 2) Relative-ish tokens: keep conservative (avoid URLs).
        candidates = set()
        for m in re.findall(
            r"(?:^|[\s\"'])([^\s\"']+\.(?:md|txt|json|yaml|yml|csv|log|sqlite3|db|bat|ps1|py|url))(?:$|[\s\"'])",
            blob,
            flags=re.IGNORECASE,
        ):
            v = (m or "").strip()
            if "://" in v or v.startswith("http"):
                continue
            candidates.add(v)

        roots = []
        if workspace_dir:
            roots.append(workspace_dir)
        if base_dir:
            roots.append(base_dir)
        for rel in sorted(candidates):
            for root in roots:
                try:
                    p = os.path.abspath(os.path.join(root, rel))
                    if os.path.exists(p):
                        self.path_seen(session_id, tool, p, kind="resolved")
                        break
                except Exception:
                    continue


def infer_success(tool_result: str) -> bool:
    """Heuristic: treat explicit Error/Permission/Not found as failure."""
    r = (tool_result or "").strip().lower()
    if not r:
        return True
    bad = (
        r.startswith("error")
        or "permission denied" in r
        or "not found" in r
        or "unknown tool" in r
        or "tool error" in r
        or "argument error" in r
    )
    return not bad
