"""Tests for cronwrap.logger module."""

import logging
import os
import tempfile
from unittest.mock import patch

import pytest

from cronwrap.logger import CronLogger


def test_cron_logger_creates_adapter():
    logger = CronLogger(job_name="test_job")
    assert logger.job_name == "test_job"
    assert logger._adapter is not None


def test_log_start_sets_start_time():
    logger = CronLogger(job_name="test_job")
    assert logger.start_time is None
    logger.log_start()
    assert logger.start_time is not None


def test_log_end_sets_end_time():
    logger = CronLogger(job_name="test_job")
    logger.log_start()
    logger.log_end(success=True)
    assert logger.end_time is not None
    assert logger.end_time >= logger.start_time


def test_log_end_without_start_does_not_crash():
    logger = CronLogger(job_name="test_job")
    # Should not raise even if log_start was never called
    logger.log_end(success=False)
    assert logger.end_time is not None


def test_info_emits_log_record(caplog):
    logger = CronLogger(job_name="my_cron", level=logging.DEBUG)
    with caplog.at_level(logging.INFO, logger="cronwrap.my_cron"):
        logger.info("hello from cron")
    assert any("hello from cron" in r.message for r in caplog.records)


def test_error_emits_log_record(caplog):
    logger = CronLogger(job_name="err_job")
    with caplog.at_level(logging.ERROR, logger="cronwrap.err_job"):
        logger.error("something went wrong")
    assert any("something went wrong" in r.message for r in caplog.records)


def test_file_handler_writes_to_file():
    with tempfile.NamedTemporaryFile(mode="r", suffix=".log", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        logger = CronLogger(job_name="file_job", log_file=tmp_path)
        logger.log_start()
        logger.info("writing to file")
        logger.log_end(success=True)

        with open(tmp_path) as f:
            content = f.read()

        assert "Job started" in content
        assert "writing to file" in content
        assert "SUCCESS" in content
    finally:
        os.unlink(tmp_path)


def test_log_level_respected(caplog):
    logger = CronLogger(job_name="level_job", level=logging.WARNING)
    with caplog.at_level(logging.DEBUG, logger="cronwrap.level_job"):
        logger.debug("debug message")
        logger.warning("warning message")
    messages = [r.message for r in caplog.records]
    assert not any("debug message" in m for m in messages)
    assert any("warning message" in m for m in messages)
