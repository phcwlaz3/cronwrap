"""Unit tests for CircuitBreaker and CircuitBreakerConfig."""
import time
from pathlib import Path

import pytest

from cronwrap.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitOpenError,
)


def test_config_defaults():
    cfg = CircuitBreakerConfig()
    assert cfg.failure_threshold == 3
    assert cfg.recovery_timeout == 300.0
    assert cfg.enabled is True


def test_config_invalid_threshold_raises():
    with pytest.raises(ValueError, match="failure_threshold"):
        CircuitBreakerConfig(failure_threshold=0)


def test_config_negative_recovery_raises():
    with pytest.raises(ValueError, match="recovery_timeout"):
        CircuitBreakerConfig(recovery_timeout=-1)


@pytest.fixture()
def cfg(tmp_path):
    return CircuitBreakerConfig(failure_threshold=2, recovery_timeout=60, state_dir=str(tmp_path))


@pytest.fixture()
def breaker(cfg):
    return CircuitBreaker("test_job", cfg)


def test_initial_state_is_closed(breaker):
    assert breaker.is_open() is False
    assert breaker.failure_count() == 0


def test_single_failure_does_not_open(breaker):
    breaker.record_failure()
    assert breaker.is_open() is False
    assert breaker.failure_count() == 1


def test_threshold_failures_opens_circuit(breaker):
    breaker.record_failure()
    breaker.record_failure()
    assert breaker.is_open() is True


def test_success_resets_circuit(breaker):
    breaker.record_failure()
    breaker.record_failure()
    assert breaker.is_open() is True
    breaker.record_success()
    assert breaker.is_open() is False
    assert breaker.failure_count() == 0


def test_reset_removes_state_file(breaker, tmp_path):
    breaker.record_failure()
    breaker.reset()
    assert not any(tmp_path.iterdir())


def test_circuit_closes_after_recovery_timeout(tmp_path):
    cfg = CircuitBreakerConfig(failure_threshold=1, recovery_timeout=0.05, state_dir=str(tmp_path))
    b = CircuitBreaker("recover_job", cfg)
    b.record_failure()
    assert b.is_open() is True
    time.sleep(0.1)
    assert b.is_open() is False


def test_state_persists_across_instances(cfg, tmp_path):
    b1 = CircuitBreaker("persist_job", cfg)
    b1.record_failure()
    b2 = CircuitBreaker("persist_job", cfg)
    assert b2.failure_count() == 1
