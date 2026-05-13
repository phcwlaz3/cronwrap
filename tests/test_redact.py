"""Tests for cronwrap.redact."""
import pytest

from cronwrap.redact import RedactConfig, Redactor, _PLACEHOLDER


# ---------------------------------------------------------------------------
# RedactConfig
# ---------------------------------------------------------------------------

def test_default_config_creates_instance():
    cfg = RedactConfig()
    assert cfg.placeholder == _PLACEHOLDER
    assert len(cfg.patterns) > 0
    assert len(cfg.redact_dict_keys) > 0


def test_empty_placeholder_raises():
    with pytest.raises(ValueError, match="placeholder"):
        RedactConfig(placeholder="")


def test_empty_patterns_raises():
    with pytest.raises(ValueError, match="patterns"):
        RedactConfig(patterns=())


# ---------------------------------------------------------------------------
# Redactor — string redaction
# ---------------------------------------------------------------------------

@pytest.fixture()
def redactor() -> Redactor:
    return Redactor()


def test_redacts_password_equals(redactor: Redactor):
    result = redactor.redact_string("password=supersecret")
    assert "supersecret" not in result
    assert _PLACEHOLDER in result


def test_redacts_token_colon(redactor: Redactor):
    result = redactor.redact_string("token: abc123xyz")
    assert "abc123xyz" not in result


def test_redacts_bearer_header(redactor: Redactor):
    result = redactor.redact_string("Authorization: Bearer eyJhbGciOiJIUzI1")
    assert "eyJhbGciOiJIUzI1" not in result


def test_plain_text_unchanged(redactor: Redactor):
    text = "hello world, nothing sensitive here"
    assert redactor.redact_string(text) == text


def test_custom_placeholder():
    cfg = RedactConfig(placeholder="***")
    r = Redactor(cfg)
    result = r.redact_string("api_key=mykey")
    assert "***" in result
    assert "mykey" not in result


# ---------------------------------------------------------------------------
# Redactor — dict redaction
# ---------------------------------------------------------------------------

def test_dict_sensitive_key_masked(redactor: Redactor):
    data = {"username": "alice", "password": "hunter2"}
    out = redactor.redact_dict(data)
    assert out["password"] == _PLACEHOLDER
    assert out["username"] == "alice"


def test_dict_case_insensitive_key(redactor: Redactor):
    data = {"Token": "secret-token-value"}
    out = redactor.redact_dict(data)
    assert out["Token"] == _PLACEHOLDER


def test_dict_string_values_are_scanned(redactor: Redactor):
    data = {"cmd": "run --password=abc123"}
    out = redactor.redact_dict(data)
    assert "abc123" not in out["cmd"]


def test_dict_non_string_values_untouched(redactor: Redactor):
    data = {"retries": 3, "enabled": True}
    out = redactor.redact_dict(data)
    assert out["retries"] == 3
    assert out["enabled"] is True


def test_dict_returns_copy(redactor: Redactor):
    data = {"password": "secret"}
    out = redactor.redact_dict(data)
    assert out is not data
    assert data["password"] == "secret"  # original unchanged
