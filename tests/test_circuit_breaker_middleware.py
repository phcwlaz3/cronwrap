"""Unit tests for CircuitBreakerMiddleware."""
import pytest

from cronwrap.circuit_breaker import CircuitBreakerConfig, CircuitOpenError
from cronwrap.circuit_breaker_middleware import CircuitBreakerMiddleware


@pytest.fixture()
def cfg(tmp_path):
    return CircuitBreakerConfig(failure_threshold=2, recovery_timeout=300, state_dir=str(tmp_path))


@pytest.fixture()
def disabled_cfg(tmp_path):
    # threshold >=1 always, so we test disabled by patching enabled property via subclass
    cfg = CircuitBreakerConfig(failure_threshold=1, recovery_timeout=0, state_dir=str(tmp_path))
    return cfg


def test_success_propagates_return_value(cfg):
    mw = CircuitBreakerMiddleware("job", cfg)
    assert mw.run(lambda: 0) == 0


def test_failure_propagates_return_value(cfg):
    mw = CircuitBreakerMiddleware("job", cfg)
    assert mw.run(lambda: 1) == 1


def test_fn_called_exactly_once(cfg):
    calls = []
    mw = CircuitBreakerMiddleware("job", cfg)
    mw.run(lambda: calls.append(1) or 0)
    assert len(calls) == 1


def test_open_circuit_raises_by_default(cfg):
    mw = CircuitBreakerMiddleware("job", cfg)
    mw.run(lambda: 1)
    mw.run(lambda: 1)  # trips threshold
    with pytest.raises(CircuitOpenError):
        mw.run(lambda: 0)


def test_open_circuit_returns_sentinel_when_not_raising(cfg):
    mw = CircuitBreakerMiddleware("job", cfg, raise_on_open=False)
    mw.run(lambda: 1)
    mw.run(lambda: 1)
    result = mw.run(lambda: 0)
    assert result == -1


def test_fn_not_called_when_circuit_open(cfg):
    calls = []
    mw = CircuitBreakerMiddleware("job", cfg, raise_on_open=False)
    mw.run(lambda: 1)
    mw.run(lambda: 1)
    mw.run(lambda: calls.append(1) or 0)
    assert len(calls) == 0


def test_success_after_open_resets(tmp_path):
    cfg = CircuitBreakerConfig(failure_threshold=1, recovery_timeout=0.0, state_dir=str(tmp_path))
    mw = CircuitBreakerMiddleware("job", cfg, raise_on_open=False)
    mw.run(lambda: 1)  # trips immediately
    # recovery_timeout=0 means circuit re-closes immediately
    result = mw.run(lambda: 0)
    assert result == 0
