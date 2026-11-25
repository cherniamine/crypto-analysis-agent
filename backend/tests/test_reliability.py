from app.core.reliability import RETRYABLE_STATUS

def test_retry_policy_only_targets_transient_statuses():
    assert 429 in RETRYABLE_STATUS
    assert 503 in RETRYABLE_STATUS
    assert 401 not in RETRYABLE_STATUS
