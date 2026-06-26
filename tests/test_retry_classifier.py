from core.retry_classifier import RetryClassifier, RetryDecision

def test_retry_classifier_permanent_exit_codes():
    classifier = RetryClassifier()
    decision = classifier.classify("Some error occurred", exit_code=1)
    assert decision.action == "abandon"
    assert "Permanent exit code 1" in decision.reason
    assert decision.max_retries == 0

    decision = classifier.classify("Some error occurred", exit_code=127)
    assert decision.action == "abandon"
    assert "exit code 127" in decision.reason

def test_retry_classifier_permanent_keywords():
    classifier = RetryClassifier()
    decision = classifier.classify("Permission denied for writing to this folder", exit_code=None)
    assert decision.action == "abandon"
    assert "permission denied" in decision.reason
    assert decision.max_retries == 0

    decision = classifier.classify("Error: File not found on host filesystem", exit_code=None)
    assert decision.action == "abandon"
    assert "not found" in decision.reason

def test_retry_classifier_transient_keywords():
    classifier = RetryClassifier()
    decision = classifier.classify("Connection timeout reached, retrying in 5 seconds", exit_code=None)
    assert decision.action == "retry"
    assert "timeout" in decision.reason
    assert decision.max_retries == 3

    decision = classifier.classify("ETIMEDOUT error occurred", exit_code=None)
    assert decision.action == "retry"
    assert "etimedout" in decision.reason

def test_retry_classifier_ambiguous():
    classifier = RetryClassifier()
    decision = classifier.classify("Unknown bizarre error occurred in script execution", exit_code=None)
    assert decision.action == "retry"
    assert "Ambiguous error" in decision.reason
    assert decision.max_retries == 2
