import os
import sys
from copy import deepcopy

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.guardrails import PathGuard
from core.runtime_config import load_config


def test_relative_paths_resolve_inside_workspace():
    cfg = load_config()
    guard = PathGuard(cfg)

    allowed, _ = guard.check_path("report.txt", operation="write")
    assert allowed

    allowed, _ = guard.check_path("workspace/report.txt", operation="write")
    assert allowed


def test_blocked_absolute_path_stays_blocked():
    cfg = deepcopy(load_config())
    cfg.setdefault("security", {})["blocked_paths"] = [r"C:\Windows"]
    guard = PathGuard(cfg)

    allowed, _ = guard.check_path(r"C:\Windows\win.ini", operation="read")
    assert not allowed


def test_hitm_false_allows_outside_workspace_writes():
    cfg = deepcopy(load_config())
    cfg.setdefault("security", {})["blocked_paths"] = []
    cfg["security"]["require_hitm_outside_workspace"] = False
    guard = PathGuard(cfg)

    allowed, _ = guard.check_path(r"C:\Temp\agenticos-policy-test.txt", operation="write")
    assert allowed
