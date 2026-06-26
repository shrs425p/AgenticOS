import pytest
from kernel.retry import retry_call


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

def test_retry_call_on_retry_callback():
    count = 0
    def failing_func():
        nonlocal count
        count += 1
        raise ValueError("Fail")

    cb_count = 0
    def cb(attempt, exc, delay):
        nonlocal cb_count
        cb_count += 1

    import pytest
    with pytest.raises(ValueError):
        retry_call(failing_func, max_retries=2, base_delay=0.01, on_retry=cb)

    assert count == 2
    assert cb_count == 1 # called once before 2nd attempt

def test_retry_call_retry_on_exception_error():
    count = 0
    def failing_func():
        nonlocal count
        count += 1
        raise ValueError("Fail")

    def bad_retry(e):
        raise TypeError("Bad")

    import pytest
    with pytest.raises(ValueError):
        # should fall back to should_retry = False and raise the original error immediately
        retry_call(failing_func, max_retries=3, base_delay=0.01, retry_on_exception=bad_retry)

    assert count == 1

def test_retry_call_on_retry_error():
    count = 0
    def failing_func():
        nonlocal count
        count += 1
        raise ValueError("Fail")

    def bad_cb(attempt, exc, delay):
        raise TypeError("Bad")

    import pytest
    with pytest.raises(ValueError):
        # should catch the error in cb and continue sleeping
        retry_call(failing_func, max_retries=2, base_delay=0.01, on_retry=bad_cb)

    assert count == 2
