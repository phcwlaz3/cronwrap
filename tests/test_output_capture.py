"""Tests for cronwrap.output_capture."""
import pytest
from cronwrap.output_capture import CaptureConfig, CapturedOutput, OutputCapture


# ---------------------------------------------------------------------------
# CaptureConfig
# ---------------------------------------------------------------------------

def test_capture_config_defaults():
    cfg = CaptureConfig()
    assert cfg.max_bytes == 1_048_576
    assert cfg.capture_stdout is True
    assert cfg.capture_stderr is True
    assert cfg.encoding == "utf-8"


def test_capture_config_negative_max_bytes_raises():
    with pytest.raises(ValueError, match="max_bytes"):
        CaptureConfig(max_bytes=-1)


def test_capture_config_zero_max_bytes_is_valid():
    cfg = CaptureConfig(max_bytes=0)
    assert cfg.max_bytes == 0


# ---------------------------------------------------------------------------
# CapturedOutput
# ---------------------------------------------------------------------------

def test_combined_joins_stdout_and_stderr():
    out = CapturedOutput(stdout="hello", stderr="world")
    assert out.combined() == "hello\nworld"


def test_combined_skips_empty_parts():
    out = CapturedOutput(stdout="only stdout", stderr="")
    assert out.combined() == "only stdout"


def test_to_dict_contains_expected_keys():
    out = CapturedOutput(stdout="a", stderr="b", exit_code=0, truncated=False)
    d = out.to_dict()
    assert set(d.keys()) == {"stdout", "stderr", "exit_code", "truncated"}
    assert d["exit_code"] == 0


# ---------------------------------------------------------------------------
# OutputCapture.run
# ---------------------------------------------------------------------------

@pytest.fixture()
def capture():
    return OutputCapture()


def test_run_captures_stdout(capture):
    result = capture.run("echo hello")
    assert "hello" in result.stdout
    assert result.exit_code == 0


def test_run_captures_stderr(capture):
    result = capture.run("echo error >&2")
    assert "error" in result.stderr


def test_run_returns_nonzero_exit_code(capture):
    result = capture.run("exit 42")
    assert result.exit_code == 42


def test_run_no_stdout_capture():
    cap = OutputCapture(CaptureConfig(capture_stdout=False))
    result = cap.run("echo hello")
    assert result.stdout == ""


def test_run_no_stderr_capture():
    cap = OutputCapture(CaptureConfig(capture_stderr=False))
    result = cap.run("echo err >&2")
    assert result.stderr == ""


def test_run_truncates_large_output():
    cap = OutputCapture(CaptureConfig(max_bytes=5))
    result = cap.run("printf 'abcdefghij'")
    assert len(result.stdout.encode("utf-8")) <= 5
    assert result.truncated is True


def test_run_not_truncated_within_limit():
    cap = OutputCapture(CaptureConfig(max_bytes=1024))
    result = cap.run("echo hi")
    assert result.truncated is False
