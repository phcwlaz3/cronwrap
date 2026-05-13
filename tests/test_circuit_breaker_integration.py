"""Integration tests: CircuitBreaker with real filesystem state."""
import time
from pathlib import Path

import pytest

from cronwrap.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
from cronwrap.circuit_breaker_middleware import CircuitBreakerMiddleware


@pytest.fixture()
def state_dir(tmp_path):
    return tmp_path


def _make_breaker(state_dir, threshold=3, timeout=60):
    cfg = CircuitBreakerConfig(
        failure_threshold=threshold,
        recovery_timeout=timeout,
        state_dir=str(state_dir),
    )
    return CircuitBreaker("integration_job", cfg)


def test_circuit_opens_after_consecutive_failures(state_dir):
    b = _make_breaker(state_dir, threshold=3)
    for _ in range(3):
        assert b.is_open() is False
        b.record_failure()
    assert b.is_open() is True


def test_circuit_recovers_after_timeout(state_dir):
    b = _make_breaker(state_dir, threshold=1, timeout=0.05)
    b.record_failure()
    assert b.is_open() is True
    time.sleep(0.1)
    assert b.is_open() is False


def test_middleware_blocks_fn_while_open(state_dir):
    cfg = CircuitBreakerConfig(failure_threshold=2, recovery_timeout=60, state_dir=str(state_dir))
    mw = CircuitBreakerMiddleware("mw_job", cfg, raise_on_open=False)
    blocked = []

    mw.run(lambda: 1)
    mw.run(lambda: 1)  # circuit opens

    for _ in range(5):
        mw.run(lambda: blocked.append(True) or 0)

    assert len(blocked) == 0


def test_state_file_created_on_failure(state_dir):
    b = _make_breaker(state_dir)
    b.record_failure()
    files = list(Path(state_dir).glob("*.json"))
    assert len(files) == 1


def test_state_file_removed_on_reset(state_dir):
    b = _make_breaker(state_dir)
    b.record_failure()
    b.reset()
    files = list(Path(state_dir).glob("*.json"))
    assert len(files) == 0
