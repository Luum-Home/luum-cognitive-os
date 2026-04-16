"""Behavioral tests verifying routing table in rules/model-routing.md matches recommender."""

from pathlib import Path
import pytest
from lib.model_recommender import ModelRecommender

ROUTING_MD = Path(__file__).parents[2] / "rules" / "model-routing.md"


@pytest.fixture(scope="module")
def routing_md_text() -> str:
    return ROUTING_MD.read_text()


@pytest.fixture(scope="module")
def rec() -> ModelRecommender:
    return ModelRecommender()


def test_recommender_haiku_tasks_align_with_routing_table(rec, routing_md_text):
    """All haiku-routed task types in recommender should align with haiku mention in rules."""
    haiku_tasks = [task for task, model in rec.ROUTING_TABLE.items() if model == "haiku"]
    assert len(haiku_tasks) > 0, "Recommender must define haiku tasks"
    # routing table in md explicitly names haiku
    assert "haiku" in routing_md_text


def test_recommender_opus_tasks_align_with_routing_table(rec, routing_md_text):
    """All opus-routed task types in recommender should align with opus mention in rules."""
    opus_tasks = [task for task, model in rec.ROUTING_TABLE.items() if model == "opus"]
    assert len(opus_tasks) > 0, "Recommender must define opus tasks"
    assert "opus" in routing_md_text


def test_haiku_cheaper_than_sonnet_cheaper_than_opus(rec):
    """Cost hierarchy must be maintained: haiku < sonnet < opus."""
    tokens = 50_000
    assert rec.estimate_cost("haiku", tokens) < rec.estimate_cost("sonnet", tokens)
    assert rec.estimate_cost("sonnet", tokens) < rec.estimate_cost("opus", tokens)


def test_archive_task_always_haiku(rec):
    """sdd-archive equivalent task must never route to expensive models."""
    for phrase in ["archive the change", "archive completed change", "archiving task"]:
        assert rec.recommend(phrase) == "haiku", (
            f"'{phrase}' should route to haiku, not {rec.recommend(phrase)}"
        )


def test_design_task_always_opus(rec):
    """Design/architecture tasks must route to opus per routing table."""
    for phrase in ["design the auth architecture", "design new service"]:
        assert rec.recommend(phrase) == "opus", (
            f"'{phrase}' should route to opus, not {rec.recommend(phrase)}"
        )


def test_implementation_task_routes_to_sonnet(rec):
    """Implementation tasks route to sonnet (not the expensive opus)."""
    model = rec.recommend("implement the new endpoint")
    assert model == "sonnet"
    assert model != "opus"
