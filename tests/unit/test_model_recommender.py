"""Unit tests for lib/model_recommender.py"""

import pytest
from lib.model_recommender import ModelRecommender


@pytest.fixture
def rec() -> ModelRecommender:
    return ModelRecommender()


# --- model recommendations ---

def test_archive_recommends_haiku(rec):
    assert rec.recommend("archive the completed change") == "haiku"


def test_format_recommends_haiku(rec):
    assert rec.recommend("format the output") == "haiku"


def test_doc_trim_recommends_haiku(rec):
    assert rec.recommend("trim docs to pointer stubs") == "haiku"


def test_rename_recommends_haiku(rec):
    assert rec.recommend("rename variables in file") == "haiku"


def test_implementation_recommends_sonnet(rec):
    assert rec.recommend("implement the new endpoint") == "sonnet"


def test_testing_recommends_sonnet(rec):
    assert rec.recommend("write unit tests for the handler") == "sonnet"


def test_architecture_recommends_opus(rec):
    assert rec.recommend("design the auth architecture") == "opus"


def test_debugging_recommends_opus(rec):
    assert rec.recommend("root cause analysis of the crash") == "opus"


def test_unknown_defaults_to_sonnet(rec):
    assert rec.recommend("do something vague") == "sonnet"


# --- cost estimation ---

def test_estimate_cost_haiku_is_cheapest(rec):
    haiku_cost = rec.estimate_cost("haiku", 50_000)
    sonnet_cost = rec.estimate_cost("sonnet", 50_000)
    opus_cost = rec.estimate_cost("opus", 50_000)
    assert haiku_cost < sonnet_cost < opus_cost


def test_estimate_cost_opus_is_most_expensive(rec):
    assert rec.estimate_cost("opus", 50_000) > rec.estimate_cost("sonnet", 50_000)


def test_estimate_cost_scales_with_tokens(rec):
    cost_50k = rec.estimate_cost("sonnet", 50_000)
    cost_100k = rec.estimate_cost("sonnet", 100_000)
    assert abs(cost_100k - 2 * cost_50k) < 1e-9


# --- savings ---

def test_savings_vs_default_shows_savings_for_haiku_task(rec):
    result = rec.savings_vs_default("trim 8 docs to stubs")
    assert result["recommended"] == "haiku"
    assert result["default"] == "sonnet"
    assert result["savings_pct"] > 0
    assert result["savings_usd"] > 0


def test_savings_vs_default_same_model_zero_savings(rec):
    result = rec.savings_vs_default("implement something", default_model="sonnet")
    assert result["recommended"] == "sonnet"
    assert result["savings_pct"] == 0.0
    assert result["savings_usd"] == 0.0


# --- task classification ---

def test_classify_task_type_archive(rec):
    assert rec.classify_task_type("archive the change") == "archive"


def test_classify_task_type_testing(rec):
    assert rec.classify_task_type("write unit tests") == "testing"


def test_classify_task_type_architecture(rec):
    assert rec.classify_task_type("design auth architecture") == "architecture"


def test_classify_task_type_unknown_defaults(rec):
    # Unknown task type should still produce a valid routing key (maps to sonnet)
    task_type = rec.classify_task_type("do something vague")
    assert rec.ROUTING_TABLE.get(task_type, "sonnet") == "sonnet"


# --- case insensitivity ---

def test_case_insensitive_archive(rec):
    assert rec.recommend("ARCHIVE the change") == "haiku"


def test_case_insensitive_debug(rec):
    assert rec.recommend("ROOT CAUSE analysis") == "opus"
