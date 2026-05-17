import pytest
from core.retry import retry_call


def test_retry_call_success():
    calls = []

    def fn():
        calls.append(1)
        return "ok"

    res = retry_call(fn, max_retries=3, base_delay=0.001)
    assert res == "ok"
    assert len(calls) == 1


def test_retry_then_success(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda s: None)
    attempts = {"count": 0}
    calls = []

    def fn():
        if attempts["count"] < 2:
            attempts["count"] += 1
            raise ValueError("transient")
        return "done"

    def retry_on(exc: Exception) -> bool:
        return isinstance(exc, ValueError)

    def on_retry(attempt: int, exc: Exception, delay: float):
        calls.append((attempt, type(exc).__name__, delay))

    res = retry_call(fn, max_retries=5, base_delay=0.001, retry_on_exception=retry_on, on_retry=on_retry)
    assert res == "done"
    assert len(calls) == 2


def test_retry_exhausts(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda s: None)

    def fn():
        raise RuntimeError("fatal")

    def retry_on(exc: Exception) -> bool:
        return True

    with pytest.raises(RuntimeError):
        retry_call(fn, max_retries=3, base_delay=0.001, retry_on_exception=retry_on)
