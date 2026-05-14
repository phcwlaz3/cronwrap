"""Tests for cronwrap.label_middleware."""
import pytest

from cronwrap.label import LabelConfig
from cronwrap.label_middleware import LabelMiddleware


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_cfg(**labels: str) -> LabelConfig:
    return LabelConfig(labels=labels)


# ---------------------------------------------------------------------------
# No selector — middleware is transparent
# ---------------------------------------------------------------------------

def test_no_selector_calls_fn():
    called = []
    mw = LabelMiddleware(_make_cfg(env="prod"))
    mw.run(lambda: called.append(True))
    assert called == [True]


def test_no_selector_propagates_return_value():
    mw = LabelMiddleware(_make_cfg(env="prod"))
    result = mw.run(lambda: 42)
    assert result == 42


def test_no_selector_empty_labels_still_calls_fn():
    called = []
    mw = LabelMiddleware(LabelConfig())
    mw.run(lambda: called.append(True))
    assert called == [True]


# ---------------------------------------------------------------------------
# With selector — labels must satisfy requirements
# ---------------------------------------------------------------------------

def test_matching_selector_calls_fn():
    called = []
    mw = LabelMiddleware(_make_cfg(env="prod", team="infra"), required={"env": "prod"})
    mw.run(lambda: called.append(True))
    assert called == [True]


def test_mismatched_value_raises_and_fn_not_called():
    called = []
    mw = LabelMiddleware(_make_cfg(env="staging"), required={"env": "prod"})
    with pytest.raises(ValueError):
        mw.run(lambda: called.append(True))
    assert called == []


def test_missing_required_key_raises_and_fn_not_called():
    called = []
    mw = LabelMiddleware(_make_cfg(team="infra"), required={"env": "prod"})
    with pytest.raises(ValueError, match="env"):
        mw.run(lambda: called.append(True))
    assert called == []


def test_empty_required_selector_always_passes():
    mw = LabelMiddleware(LabelConfig(), required={})
    assert mw.run(lambda: "ok") == "ok"


def test_fn_called_exactly_once_when_selector_matches():
    count = [0]

    def _fn():
        count[0] += 1

    mw = LabelMiddleware(_make_cfg(env="prod"), required={"env": "prod"})
    mw.run(_fn)
    assert count[0] == 1


def test_error_message_contains_missing_key_name():
    mw = LabelMiddleware(_make_cfg(team="infra"), required={"env": "prod", "region": "us"})
    with pytest.raises(ValueError) as exc_info:
        mw.run(lambda: None)
    msg = str(exc_info.value)
    assert "env" in msg or "region" in msg
