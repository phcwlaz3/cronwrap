"""Tests for cronwrap.label."""
import pytest

from cronwrap.label import (
    LabelConfig,
    LabelMatcher,
    labels_from_str,
    labels_to_str,
    merge_labels,
)


# ---------------------------------------------------------------------------
# LabelConfig
# ---------------------------------------------------------------------------

def test_label_config_defaults_to_empty_dict():
    cfg = LabelConfig()
    assert cfg.labels == {}


def test_label_config_accepts_valid_labels():
    cfg = LabelConfig(labels={"env": "prod", "team": "infra"})
    assert cfg.labels["env"] == "prod"


def test_label_config_strips_whitespace():
    cfg = LabelConfig(labels={" env ": " prod "})
    assert "env" in cfg.labels
    assert cfg.labels["env"] == "prod"


def test_label_config_rejects_non_dict():
    with pytest.raises(TypeError):
        LabelConfig(labels=["env=prod"])  # type: ignore[arg-type]


def test_label_config_rejects_blank_key():
    with pytest.raises(ValueError):
        LabelConfig(labels={"": "value"})


def test_label_config_rejects_non_string_value():
    with pytest.raises(TypeError):
        LabelConfig(labels={"env": 42})  # type: ignore[dict-item]


# ---------------------------------------------------------------------------
# LabelMatcher
# ---------------------------------------------------------------------------

def test_matcher_returns_true_when_all_required_present():
    matcher = LabelMatcher({"env": "prod"})
    assert matcher.matches({"env": "prod", "team": "infra"}) is True


def test_matcher_returns_false_when_value_differs():
    matcher = LabelMatcher({"env": "prod"})
    assert matcher.matches({"env": "staging"}) is False


def test_matcher_returns_false_when_key_missing():
    matcher = LabelMatcher({"env": "prod"})
    assert matcher.matches({"team": "infra"}) is False


def test_matcher_empty_required_always_matches():
    matcher = LabelMatcher({})
    assert matcher.matches({}) is True
    assert matcher.matches({"env": "prod"}) is True


def test_missing_keys_returns_absent_keys():
    matcher = LabelMatcher({"env": "prod", "region": "us"})
    missing = matcher.missing_keys({"env": "prod"})
    assert missing == frozenset({"region"})


# ---------------------------------------------------------------------------
# merge_labels
# ---------------------------------------------------------------------------

def test_merge_labels_later_wins():
    result = merge_labels({"env": "staging"}, {"env": "prod", "team": "infra"})
    assert result == {"env": "prod", "team": "infra"}


def test_merge_labels_empty_sources():
    assert merge_labels() == {}


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------

def test_labels_to_str_sorts_keys():
    result = labels_to_str({"team": "infra", "env": "prod"})
    assert result == "env=prod,team=infra"


def test_labels_to_str_empty():
    assert labels_to_str({}) == ""


def test_labels_from_str_round_trips():
    raw = "env=prod,team=infra"
    assert labels_from_str(raw) == {"env": "prod", "team": "infra"}


def test_labels_from_str_empty_string():
    assert labels_from_str("") == {}


def test_labels_from_str_invalid_segment_raises():
    with pytest.raises(ValueError, match="key=value"):
        labels_from_str("env-prod")
