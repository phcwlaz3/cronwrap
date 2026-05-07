"""Tests for cronwrap.tag_filter."""
import pytest

from cronwrap.tag_filter import TagFilter, TagFilterConfig


# ---------------------------------------------------------------------------
# TagFilterConfig
# ---------------------------------------------------------------------------

class TestTagFilterConfig:
    def test_defaults_are_empty_frozensets(self):
        cfg = TagFilterConfig()
        assert cfg.include == frozenset()
        assert cfg.exclude == frozenset()

    def test_accepts_lists(self):
        cfg = TagFilterConfig(include=["a", "b"], exclude=["c"])
        assert "a" in cfg.include
        assert "c" in cfg.exclude

    def test_overlap_raises(self):
        with pytest.raises(ValueError, match="include and exclude"):
            TagFilterConfig(include=["prod"], exclude=["prod"])

    def test_is_immutable(self):
        cfg = TagFilterConfig(include=["x"])
        with pytest.raises(AttributeError):
            cfg.include = frozenset()  # type: ignore[misc]


# ---------------------------------------------------------------------------
# TagFilter.should_run
# ---------------------------------------------------------------------------

class TestTagFilterShouldRun:
    def test_no_filter_always_runs(self):
        f = TagFilter()
        assert f.should_run(["prod", "nightly"]) is True
        assert f.should_run([]) is True

    def test_include_filter_allows_matching_job(self):
        f = TagFilter(TagFilterConfig(include=["nightly"]))
        assert f.should_run(["nightly", "prod"]) is True

    def test_include_filter_blocks_non_matching_job(self):
        f = TagFilter(TagFilterConfig(include=["nightly"]))
        assert f.should_run(["hourly"]) is False

    def test_include_filter_blocks_job_with_no_tags(self):
        f = TagFilter(TagFilterConfig(include=["nightly"]))
        assert f.should_run([]) is False

    def test_exclude_filter_blocks_matching_job(self):
        f = TagFilter(TagFilterConfig(exclude=["disabled"]))
        assert f.should_run(["disabled", "prod"]) is False

    def test_exclude_filter_allows_non_matching_job(self):
        f = TagFilter(TagFilterConfig(exclude=["disabled"]))
        assert f.should_run(["prod"]) is True

    def test_exclude_takes_priority_over_include(self):
        # A tag in *exclude* wins even if another tag is in *include*.
        f = TagFilter(TagFilterConfig(include=["prod"], exclude=["skip"]))
        assert f.should_run(["prod", "skip"]) is False

    def test_combined_include_and_exclude(self):
        f = TagFilter(TagFilterConfig(include=["prod"], exclude=["slow"]))
        assert f.should_run(["prod"]) is True
        assert f.should_run(["staging"]) is False
        assert f.should_run(["prod", "slow"]) is False


# ---------------------------------------------------------------------------
# TagFilter.matching_tags
# ---------------------------------------------------------------------------

class TestTagFilterMatchingTags:
    def test_no_include_returns_all_tags(self):
        f = TagFilter()
        assert f.matching_tags(["a", "b"]) == frozenset({"a", "b"})

    def test_returns_intersection_with_include(self):
        f = TagFilter(TagFilterConfig(include=["prod", "nightly"]))
        assert f.matching_tags(["nightly", "hourly"]) == frozenset({"nightly"})

    def test_returns_empty_when_no_overlap(self):
        f = TagFilter(TagFilterConfig(include=["prod"]))
        assert f.matching_tags(["staging"]) == frozenset()
