# SCOPE: both
"""Behavior proof for hooks/pending-truth-drift-detector.sh (ADR-273 Slice C).

This hook is the busiest of the observe-only family — 975 invocations across
the live and rotated `hook-timing` ledgers — and it always exits 0, so the
exit code says nothing about whether it ever nudged anybody.  Its whole output
is one line of JSON on stdout that the harness parses as
``hookSpecificOutput.additionalContext``.  Two regressions are invisible
without a test: the matcher stops matching (silence forever, indistinguishable
from "nothing to say"), or the emission stops being valid JSON (the harness
drops it, still silently).

Both are asserted here against a synthetic ledger.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HOOK = REPO / "hooks" / "pending-truth-drift-detector.sh"

LEDGER_REL = "docs/06-Daily/reports/pending-truth-latest.json"

OPEN_ITEM = {
    "id": "PT-OPEN",
    "status": "verified-pending",
    "source": "docs/plan-x.md",
    "next_action": "wire lib/target_module.py into the readiness gate",
    "evidence": [{"path": "lib/target_module.py"}],
}
CLOSED_ITEM = {
    "id": "PT-CLOSED",
    "status": "verified-done",
    "source": "docs/plan-y.md",
    "next_action": "already done for lib/target_module.py",
    "evidence": [{"path": "lib/target_module.py"}],
}


def _project(tmp_path: Path, items: list[dict]) -> Path:
    ledger = tmp_path / LEDGER_REL
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text(json.dumps({"items": items}), encoding="utf-8")
    (tmp_path / "lib").mkdir(exist_ok=True)
    return tmp_path


def _run(project: Path, payload: dict) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(
        {
            "COGNITIVE_OS_PROJECT_DIR": str(project),
            "CLAUDE_PROJECT_DIR": str(project),
            "CODEX_PROJECT_DIR": str(project),
        }
    )
    return subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        cwd=project,
        env=env,
        timeout=30,
        check=False,
    )


def _edit(project: Path, rel: str) -> dict:
    return {
        "tool_name": "Edit",
        "tool_input": {"file_path": str(project / rel)},
        "tool_response": {},
    }


def test_editing_a_file_named_by_an_open_item_emits_a_parseable_nudge(tmp_path: Path) -> None:
    project = _project(tmp_path, [OPEN_ITEM])

    result = _run(project, _edit(project, "lib/target_module.py"))

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip(), "an edit that touches an open ledger item must produce a nudge"
    emitted = json.loads(result.stdout)  # invalid JSON here is the silent-drop regression
    block = emitted["hookSpecificOutput"]
    assert block["hookEventName"] == "PostToolUse"
    context = block["additionalContext"]
    assert "PT-OPEN" in context, "the nudge must name the item it thinks may be closable"
    assert "lib/target_module.py" in context
    assert str(project) not in context, "the path must be repo-relative, not machine-absolute"


def test_closed_items_never_nudge(tmp_path: Path) -> None:
    """A ledger of already-settled items is exactly the case that must stay quiet."""
    project = _project(tmp_path, [CLOSED_ITEM])

    result = _run(project, _edit(project, "lib/target_module.py"))

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "", (
        f"verified-done items must not be re-nudged; got: {result.stdout!r}"
    )


def test_only_the_open_item_is_reported_when_both_exist(tmp_path: Path) -> None:
    project = _project(tmp_path, [CLOSED_ITEM, OPEN_ITEM])

    result = _run(project, _edit(project, "lib/target_module.py"))

    context = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
    assert "PT-OPEN" in context
    assert "PT-CLOSED" not in context


def test_an_unrelated_edit_stays_silent(tmp_path: Path) -> None:
    project = _project(tmp_path, [OPEN_ITEM])

    result = _run(project, _edit(project, "lib/unrelated_module.py"))

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "", (
        f"a file no ledger item mentions must not produce a nudge; got: {result.stdout!r}"
    )


def test_no_ledger_means_no_output_and_no_failure(tmp_path: Path) -> None:
    """Consumer projects have no ledger; the hook must be a no-op there, not noise."""
    (tmp_path / "lib").mkdir()

    result = _run(tmp_path, _edit(tmp_path, "lib/target_module.py"))

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == ""
