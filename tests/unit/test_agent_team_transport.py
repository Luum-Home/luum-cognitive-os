from __future__ import annotations

import pytest

from lib.agent_team_transport import transport_plan


def test_file_transport_is_active_and_losslessly_maps_to_upgrade_targets() -> None:
    plan = transport_plan(team_name="release", backend="file").to_dict()
    assert plan["schema_version"] == "agent-team-transport-plan/v1"
    assert plan["status"] == "active"
    assert plan["compatibility"]["requires_daemon"] is False
    assert plan["compatibility"]["lossless_to"] == ["nats", "a2a"]


def test_nats_and_a2a_are_opt_in_upgrade_targets_without_default_deps() -> None:
    nats = transport_plan(team_name="release", backend="nats").to_dict()
    a2a = transport_plan(team_name="release", backend="a2a").to_dict()
    assert nats["status"] == "upgrade_target"
    assert "opt-in-only" in nats["dependency_policy"]
    assert a2a["subject_mapping"]["handoffs"] == "A2A message part carrying handoff-envelope/v1"


def test_transport_plan_rejects_unsafe_team_name() -> None:
    with pytest.raises(ValueError):
        transport_plan(team_name="../bad", backend="file")
