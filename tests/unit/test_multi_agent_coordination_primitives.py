from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

import pytest

from lib.session_bus import append_event, read_events
from lib.task_claim_ledger import acquire_claim, list_claims, release_claim
from scripts.orphan_overwrite_detector import overwritten_paths

pytestmark = pytest.mark.unit

REPO = Path(__file__).resolve().parents[2]


def load_derived_gate():
    spec = importlib.util.spec_from_file_location("derived_artifact_gate", REPO / "scripts" / "derived_artifact_gate.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_session_bus_appends_and_filters_events(tmp_path: Path) -> None:
    append_event("registry_changed", {"file": "cognitive-os.yaml"}, project_dir=tmp_path, session_id="s1")
    append_event("projection_regenerated", {"file": ".codex/hooks.json"}, project_dir=tmp_path, session_id="s2")

    all_events = read_events(project_dir=tmp_path)
    filtered = read_events(project_dir=tmp_path, event_type="projection_regenerated")

    assert [event["event_type"] for event in all_events] == ["registry_changed", "projection_regenerated"]
    assert len(filtered) == 1
    assert filtered[0]["payload"]["file"] == ".codex/hooks.json"


def test_task_claim_ledger_rejects_duplicate_active_claim(tmp_path: Path) -> None:
    first = acquire_claim(tmp_path, task_id="task-1", session_id="s1", agent_id="a1", scope="ADR-116/P1.1")
    second = acquire_claim(tmp_path, task_id="task-1", session_id="s2", agent_id="a2", scope="ADR-116/P1.1")

    assert first.status == "acquired"
    assert second.status == "blocked"
    assert second.held_by and second.held_by["session_id"] == "s1"
    assert [claim["task_id"] for claim in list_claims(tmp_path)] == ["task-1"]


def test_task_claim_release_allows_new_holder(tmp_path: Path) -> None:
    assert acquire_claim(tmp_path, task_id="task-1", session_id="s1", agent_id="a1").status == "acquired"
    assert release_claim(tmp_path, task_id="task-1", session_id="s1").status == "released"

    result = acquire_claim(tmp_path, task_id="task-1", session_id="s2", agent_id="a2")

    assert result.status == "acquired"
    assert result.claim and result.claim["session_id"] == "s2"


def test_derived_gate_requires_staged_artifact_closure(monkeypatch: pytest.MonkeyPatch) -> None:
    gate = load_derived_gate()
    monkeypatch.setattr(gate, "changed_staged", lambda: {"cognitive-os.yaml"})
    failures: list[str] = []

    gate.check_staged_closure(failures)

    assert failures
    assert "manifests/hook-quality.yaml" in failures[0]
    assert ".claude/settings.json" in failures[0]
    assert ".codex/hooks.json" in failures[0]


def test_orphan_overwrite_detector_reports_changed_paths_between_commits(tmp_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    target = tmp_path / "file.txt"
    target.write_text("one\n", encoding="utf-8")
    subprocess.run(["git", "add", "file.txt"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "one"], cwd=tmp_path, check=True, capture_output=True)
    before = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=tmp_path, text=True).strip()
    target.write_text("two\n", encoding="utf-8")
    subprocess.run(["git", "commit", "-am", "two"], cwd=tmp_path, check=True, capture_output=True)

    assert overwritten_paths(tmp_path, before, "HEAD") == ["file.txt"]


def test_merge_to_main_help_documents_single_writer_lock() -> None:
    result = subprocess.run(
        ["bash", str(REPO / "scripts" / "merge-to-main.sh"), "--help"],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "main-merge.lock" in result.stdout
    assert "single-writer" in result.stdout


def test_merge_to_main_refuses_validation_dirty_worktree() -> None:
    text = (REPO / "scripts" / "merge-to-main.sh").read_text(encoding="utf-8")

    assert "validation dirtied tracked worktree" in text
    assert "status --porcelain=v1 --untracked-files=no" in text
