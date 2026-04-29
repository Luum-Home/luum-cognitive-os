"""Behavior tests for the governed self-improvement CLI."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT_ROOT / "scripts" / "cos-governed-self-improvement.py"


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def _run(project_dir: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", str(SCRIPT), "--project-dir", str(project_dir), *args],
        cwd=str(PROJECT_ROOT),
        text=True,
        capture_output=True,
        timeout=20,
    )


def test_cli_suggest_draft_inspect_and_promote(tmp_path: Path) -> None:
    _write_jsonl(
        tmp_path / ".cognitive-os" / "metrics" / "error-learning.jsonl",
        [
            {"type": "TEST_FAILURE", "service": "checkout"},
            {"type": "TEST_FAILURE", "service": "checkout"},
            {"type": "TEST_FAILURE", "service": "checkout"},
        ],
    )

    suggest = _run(tmp_path, "suggest")
    assert suggest.returncode == 0, suggest.stderr
    signals = json.loads(suggest.stdout)
    assert signals[0]["slug"] == "repair-test-failure-checkout"

    draft = _run(tmp_path, "draft", "repair-test-failure-checkout")
    assert draft.returncode == 0, draft.stderr
    draft_payload = json.loads(draft.stdout)
    assert draft_payload["status"] == "draft"

    inspect = _run(tmp_path, "inspect", "repair-test-failure-checkout")
    assert inspect.returncode == 0, inspect.stderr
    assert json.loads(inspect.stdout)["draft_id"] == "repair-test-failure-checkout"

    denied = _run(tmp_path, "promote", "repair-test-failure-checkout")
    assert denied.returncode != 0
    assert "promotion requires" in denied.stderr

    promoted = _run(
        tmp_path,
        "promote",
        "repair-test-failure-checkout",
        "--approved-by",
        "behavior-test",
    )
    assert promoted.returncode == 0, promoted.stderr
    payload = json.loads(promoted.stdout)
    assert payload["target"] == ".cognitive-os/skills/cos/repair-test-failure-checkout/SKILL.md"
    assert (tmp_path / payload["target"]).exists()
