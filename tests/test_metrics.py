"""Tests for cronwrap.metrics module."""

from datetime import datetime, timedelta
import pytest

from cronwrap.metrics import JobMetrics, MetricsCollector


# ---------------------------------------------------------------------------
# JobMetrics tests
# ---------------------------------------------------------------------------

def test_duration_returns_none_without_times():
    m = JobMetrics(job_name="backup")
    assert m.duration is None
    assert m.duration_seconds is None


def test_duration_calculated_correctly():
    start = datetime(2024, 1, 1, 12, 0, 0)
    end = datetime(2024, 1, 1, 12, 0, 45)
    m = JobMetrics(job_name="backup", start_time=start, end_time=end)
    assert m.duration == timedelta(seconds=45)
    assert m.duration_seconds == 45.0


def test_succeeded_none_when_exit_code_unknown():
    m = JobMetrics(job_name="backup")
    assert m.succeeded is None


def test_succeeded_true_for_zero_exit_code():
    m = JobMetrics(job_name="backup", exit_code=0)
    assert m.succeeded is True


def test_succeeded_false_for_nonzero_exit_code():
    m = JobMetrics(job_name="backup", exit_code=1)
    assert m.succeeded is False


def test_to_dict_contains_expected_keys():
    start = datetime(2024, 6, 1, 8, 0, 0)
    end = datetime(2024, 6, 1, 8, 0, 10)
    m = JobMetrics(
        job_name="sync",
        start_time=start,
        end_time=end,
        exit_code=0,
        attempt=2,
        retries=1,
        tags={"env": "prod"},
    )
    d = m.to_dict()
    assert d["job_name"] == "sync"
    assert d["duration_seconds"] == 10.0
    assert d["exit_code"] == 0
    assert d["succeeded"] is True
    assert d["attempt"] == 2
    assert d["retries"] == 1
    assert d["tags"] == {"env": "prod"}
    assert d["start_time"] == start.isoformat()
    assert d["end_time"] == end.isoformat()


# ---------------------------------------------------------------------------
# MetricsCollector tests
# ---------------------------------------------------------------------------

@pytest.fixture
def collector():
    return MetricsCollector()


def test_collector_starts_empty(collector):
    assert collector.all() == []


def test_collector_records_metrics(collector):
    m = JobMetrics(job_name="job1", exit_code=0)
    collector.record(m)
    assert len(collector.all()) == 1


def test_collector_filters_by_job_name(collector):
    collector.record(JobMetrics(job_name="job1", exit_code=0))
    collector.record(JobMetrics(job_name="job2", exit_code=1))
    collector.record(JobMetrics(job_name="job1", exit_code=0))
    assert len(collector.for_job("job1")) == 2
    assert len(collector.for_job("job2")) == 1


def test_success_rate_none_when_no_data(collector):
    assert collector.success_rate("unknown") is None


def test_success_rate_all_success(collector):
    for _ in range(4):
        collector.record(JobMetrics(job_name="j", exit_code=0))
    assert collector.success_rate("j") == 1.0


def test_success_rate_mixed(collector):
    collector.record(JobMetrics(job_name="j", exit_code=0))
    collector.record(JobMetrics(job_name="j", exit_code=1))
    collector.record(JobMetrics(job_name="j", exit_code=0))
    assert collector.success_rate("j") == pytest.approx(2 / 3)


def test_collector_clear(collector):
    collector.record(JobMetrics(job_name="j", exit_code=0))
    collector.clear()
    assert collector.all() == []
