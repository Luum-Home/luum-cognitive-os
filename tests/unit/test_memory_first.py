"""Unit tests for lib/memory_first.py."""
import pytest
from lib.memory_first import MemoryFirst


@pytest.fixture()
def m() -> MemoryFirst:
    return MemoryFirst()


def test_remember_and_recall(m):
    m.remember("phase", "reconstruction")
    assert m.recall("phase") == "reconstruction"


def test_recall_missing(m):
    assert m.recall("nonexistent") is None


def test_has_true(m):
    m.remember("x", "y")
    assert m.has("x") is True


def test_has_false(m):
    assert m.has("missing") is False


def test_should_search_cached(m):
    m.remember("phase", "reconstruction")
    assert m.should_search_engram("phase") is False


def test_should_search_uncached(m):
    assert m.should_search_engram("auth") is True


def test_should_read_active_tasks(m):
    result = m.should_read_file(".cognitive-os/tasks/active-tasks.json", "check tasks")
    assert result["action"] == "skip"
    assert "SmartAccess" in result["suggestion"]


def test_should_read_jsonl(m):
    result = m.should_read_file("metrics/error-learning.jsonl", "find errors")
    assert result["action"] == "skip"
    assert "grep" in result["suggestion"].lower() or "tail" in result["suggestion"].lower()


def test_should_read_metrics_jsonl_glob(m):
    """Files matching .cognitive-os/metrics/*.jsonl pattern are restricted."""
    result = m.should_read_file(".cognitive-os/metrics/skill-metrics.jsonl")
    assert result["action"] == "skip"


def test_should_read_normal_file(m):
    result = m.should_read_file("lib/smart_access.py", "read module")
    assert result["action"] == "read_full"


def test_pre_action_check_mem_search_cached(m):
    m.remember("phase", "reconstruction")
    warning = m.pre_action_check("mem_search", "phase")
    assert warning is not None
    assert "Already known" in warning
    assert "reconstruction" in warning


def test_pre_action_check_read_jsonl(m):
    warning = m.pre_action_check("Read", "metrics/error-learning.jsonl")
    assert warning is not None
    assert "JSONL" in warning or "grep" in warning.lower() or "tail" in warning.lower()


def test_pre_action_check_normal(m):
    assert m.pre_action_check("Read", "lib/smart_access.py") is None


def test_pre_action_check_bash_cat_jsonl(m):
    warning = m.pre_action_check("Bash", "cat metrics/error-learning.jsonl")
    assert warning is not None


def test_format_cache_summary(m):
    m.remember("phase", "reconstruction")
    m.remember("config", "loaded")
    summary = m.format_cache_summary()
    assert "2 items" in summary
    assert "phase" in summary


def test_serialization_roundtrip(m):
    m.remember("phase", "reconstruction")
    m.remember("stack", "go+ts")
    data = m.to_dict()
    restored = MemoryFirst.from_dict(data)
    assert restored.recall("phase") == "reconstruction"
    assert restored.recall("stack") == "go+ts"
    assert restored.has("phase") is True


def test_empty_cache(m):
    summary = m.format_cache_summary()
    assert "0 items" in summary


def test_pre_action_check_mem_get_observation_cached(m):
    m.remember("planning/ws14b/spec", "spec content here")
    warning = m.pre_action_check("mem_get_observation", "planning/ws14b/spec")
    assert warning is not None
    assert "Already known" in warning


def test_pre_action_check_uncached_mem_search(m):
    assert m.pre_action_check("mem_search", "unknown-topic") is None
