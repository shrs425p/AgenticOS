from kernel.errors import RateLimitExhausted

def test_exceptions():
    try:
        raise RateLimitExhausted("Test error")
    except RateLimitExhausted as e:
        assert str(e) == "Test error"
