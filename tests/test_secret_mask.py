"""Tests for cronwrap.secret_mask."""
import pytest

from cronwrap.secret_mask import SecretMasker, SecretMaskConfig


# ---------------------------------------------------------------------------
# SecretMaskConfig
# ---------------------------------------------------------------------------

def test_default_config_creates_instance():
    cfg = SecretMaskConfig()
    assert cfg.mask == "***"
    assert cfg.extra_patterns == []


def test_empty_mask_raises():
    with pytest.raises(ValueError, match="mask"):
        SecretMaskConfig(mask="")


# ---------------------------------------------------------------------------
# SecretMasker.mask
# ---------------------------------------------------------------------------

@pytest.fixture()
def masker() -> SecretMasker:
    return SecretMasker()


def test_masks_password_equals(masker):
    result = masker.mask("password=supersecret")
    assert "supersecret" not in result
    assert "***" in result


def test_masks_token_colon(masker):
    result = masker.mask("token: abc123xyz")
    assert "abc123xyz" not in result


def test_masks_bearer_token(masker):
    result = masker.mask("Authorization: Bearer eyJhbGci.payload.sig")
    assert "eyJhbGci" not in result


def test_plain_text_unchanged(masker):
    text = "this is a normal log line"
    assert masker.mask(text) == text


def test_extra_pattern_is_applied():
    cfg = SecretMaskConfig(extra_patterns=[r"(?i)ssn[=:\s]+\S+"])
    m = SecretMasker(cfg)
    result = m.mask("ssn=123-45-6789")
    assert "123-45-6789" not in result
    assert "***" in result


def test_custom_mask_string():
    cfg = SecretMaskConfig(mask="<REDACTED>")
    m = SecretMasker(cfg)
    result = m.mask("api_key=mykey")
    assert "<REDACTED>" in result
    assert "mykey" not in result


# ---------------------------------------------------------------------------
# SecretMasker.mask_dict
# ---------------------------------------------------------------------------

def test_mask_dict_masks_string_values(masker):
    data = {"password": "password=secret", "count": 42}
    result = masker.mask_dict(data)
    assert "secret" not in result["password"]
    assert result["count"] == 42  # non-string unchanged


def test_mask_dict_returns_copy(masker):
    data = {"info": "safe text"}
    result = masker.mask_dict(data)
    assert result is not data


# ---------------------------------------------------------------------------
# SecretMasker.mask_env
# ---------------------------------------------------------------------------

def test_mask_env_replaces_sensitive_keys(masker):
    env = {"HOME": "/root", "DB_PASSWORD": "hunter2", "PATH": "/usr/bin"}
    result = masker.mask_env(env, sensitive_keys=["DB_PASSWORD"])
    assert result["DB_PASSWORD"] == "***"
    assert result["HOME"] == "/root"
    assert result["PATH"] == "/usr/bin"


def test_mask_env_is_case_insensitive_for_keys(masker):
    env = {"API_KEY": "topsecret"}
    result = masker.mask_env(env, sensitive_keys=["api_key"])
    assert result["API_KEY"] == "***"


def test_mask_env_empty_sensitive_keys_leaves_env_unchanged(masker):
    env = {"FOO": "bar"}
    assert masker.mask_env(env, sensitive_keys=[]) == env
