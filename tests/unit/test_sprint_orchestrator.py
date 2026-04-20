"""Unit tests for lib.sprint_orchestrator (ADR-036 MVP)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Repo-root import shim, matches other tests in this suite.
_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from lib.harness_adapter.base import CanonicalEvent  # noqa: E402
from lib.sprint_orchestrator import (  # noqa: E402
    CommitStrategy,
    SprintCancelled,
    SprintCompleted,
    SprintManifest,
    SprintSpecError,
    SprintStarted,
    SprintStatus,
    SprintTask,
    SprintTaskCompleted,
    SprintTaskLaunched,
    default_sprints_dir,
    list_manifests,
    load_manifest,
    load_spec,
    manifest_path,
    save_manifest,
    transition,
)


EXAMPLE_SPEC = _REPO / ".cognitive-os/sprints/example-sprint.yaml"


def test_load_spec_parses_example(tmp_path: Path) -> None:
    manifest = load_spec(EXAMPLE_SPEC)
    assert manifest.name == "example-mvp-sprint"
    assert manifest.status == SprintStatus.PENDING.value
    assert manifest.commit_strategy == CommitStrategy.PER_TASK.value
    assert len(manifest.tasks) == 3
    ids = [t.id for t in manifest.tasks]
    assert ids == ["fix-login-bug", "refactor-cache-layer", "update-docs-rate-limits"]
    models = [t.model for t in manifest.tasks]
    assert models == ["sonnet", "opus", "haiku"]
    assert manifest.tasks[0].file_scope == [
        "src/auth/login.py",
        "tests/unit/test_login.py",
    ]
    assert manifest.id.startswith("sprint-")


def test_load_spec_rejects_missing_name(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text("tasks:\n  - title: t\n    prompt: p\n", encoding="utf-8")
    with pytest.raises(SprintSpecError, match="name"):
        load_spec(bad)


def test_load_spec_rejects_empty_tasks(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text('name: "x"\ntasks:\n', encoding="utf-8")
    with pytest.raises(SprintSpecError, match="tasks"):
        load_spec(bad)


def test_load_spec_rejects_bad_commit_strategy(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        'name: "x"\ncommit_strategy: bogus\ntasks:\n  - title: t\n    prompt: p\n',
        encoding="utf-8",
    )
    with pytest.raises(SprintSpecError, match="commit_strategy"):
        load_spec(bad)


def test_manifest_roundtrip(tmp_path: Path) -> None:
    manifest = load_spec(EXAMPLE_SPEC)
    p = tmp_path / "manifest.json"
    save_manifest(manifest, p)
    loaded = load_manifest(p)
    assert loaded.id == manifest.id
    assert loaded.name == manifest.name
    assert len(loaded.tasks) == len(manifest.tasks)
    assert isinstance(loaded.tasks[0], SprintTask)
    assert loaded.tasks[0].id == manifest.tasks[0].id
    # Dict-level equality of structure.
    assert loaded.to_dict() == manifest.to_dict()


def test_state_transitions_happy_path() -> None:
    m = SprintManifest(id="s1", name="test")
    assert m.status == SprintStatus.PENDING.value
    transition(m, SprintStatus.RUNNING.value)
    assert m.status == SprintStatus.RUNNING.value
    assert m.started_at is not None
    transition(m, SprintStatus.COMPLETED.value)
    assert m.status == SprintStatus.COMPLETED.value
    assert m.ended_at is not None


def test_state_transitions_rejects_illegal() -> None:
    m = SprintManifest(id="s1", name="test", status=SprintStatus.COMPLETED.value)
    with pytest.raises(ValueError, match="illegal"):
        transition(m, SprintStatus.RUNNING.value)

    m2 = SprintManifest(id="s2", name="test")
    with pytest.raises(ValueError, match="illegal"):
        transition(m2, SprintStatus.COMPLETED.value)  # pending → completed not allowed


def test_event_schema_roundtrip_via_registry() -> None:
    events = [
        SprintStarted(sprint_id="s1", sprint_name="n", task_count=2, started_at=1.0),
        SprintTaskLaunched(sprint_id="s1", task_id="t1", agent_id="a1", launched_at=2.0),
        SprintTaskCompleted(sprint_id="s1", task_id="t1", agent_id="a1", ended_at=3.0),
        SprintCancelled(sprint_id="s1", cancelled_at=4.0, reason="user"),
        SprintCompleted(sprint_id="s1", ended_at=5.0, tasks_succeeded=1, tasks_failed=0),
    ]
    for ev in events:
        data = ev.to_dict()
        assert data["event_type"] == ev.event_type
        restored = CanonicalEvent.from_dict(data)
        assert type(restored) is type(ev)
        assert restored.to_dict() == data


def test_list_manifests_skips_corrupt(tmp_path: Path) -> None:
    sprints_dir = tmp_path / ".cognitive-os" / "sprints"
    sprints_dir.mkdir(parents=True)

    good = SprintManifest(id="good", name="g")
    (sprints_dir / "good.json").write_text(good.to_json(), encoding="utf-8")
    (sprints_dir / "bad.json").write_text("not json at all {", encoding="utf-8")

    found = list_manifests(tmp_path)
    ids = [m.id for m in found]
    assert "good" in ids
    assert "bad" not in ids


def test_manifest_path_uses_project_dir(tmp_path: Path) -> None:
    p = manifest_path("sprint-xyz", tmp_path)
    assert p == tmp_path / ".cognitive-os" / "sprints" / "sprint-xyz.json"
    assert default_sprints_dir(tmp_path) == tmp_path / ".cognitive-os" / "sprints"
