import os
import sys
from collections import defaultdict, deque

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import core.model_clients as model_clients


def test_model_specific_rpm_overrides_provider_rpm():
    cfg = {
        "rate_limits": {
            "enabled": True,
            "safety_factor": 1.0,
            "providers": {"nvidia": {"rpm": 40}},
            "models": {"nvidia:special": {"rpm": 10}},
        }
    }

    assert model_clients._configured_rpm(cfg, "nvidia", "special") == 10
    assert model_clients._configured_rpm(cfg, "nvidia", "other") == 40


def test_missing_rpm_means_unlimited():
    cfg = {"rate_limits": {"enabled": True, "providers": {}, "models": {}}}

    assert model_clients._configured_rpm(cfg, "nvidia", "anything") == 0.0


def test_unique_sorted_model_ids_deduplicates():
    assert model_clients._unique_sorted_model_ids(["b", "a", "b", "", None]) == [
        "a",
        "b",
    ]


def test_rate_limiter_uses_effective_rpm_window(monkeypatch):
    cfg = {
        "rate_limits": {
            "enabled": True,
            "safety_factor": 1.0,
            "window_seconds": 60,
            "providers": {"nvidia": {"rpm": 2}},
        }
    }
    clock = {"now": 0.0, "slept": 0.0}

    def fake_monotonic():
        return clock["now"]

    def fake_sleep(seconds):
        clock["slept"] += seconds
        clock["now"] += seconds

    monkeypatch.setattr(model_clients.time, "monotonic", fake_monotonic)
    monkeypatch.setattr(model_clients.time, "sleep", fake_sleep)
    monkeypatch.setattr(model_clients, "_RATE_LIMIT_HISTORY", defaultdict(deque))

    model_clients._wait_for_rate_limit(cfg, "nvidia", "model")
    model_clients._wait_for_rate_limit(cfg, "nvidia", "model")
    model_clients._wait_for_rate_limit(cfg, "nvidia", "model")

    assert clock["slept"] == 60
