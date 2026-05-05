from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from lib.governed_self_improvement import suggest_improvement_signals
from lib.key_learning_capture import build_records, extract_key_learnings

pytestmark = pytest.mark.unit

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "cos-key-learnings-capture"


def test_extracts_numbered_key_learnings_only() -> None:
    markdown = """Done.

## Key Learnings:

1. ADR slices should be implemented one at a time.
2. Guard maturity must start warn before block.

::git-commit{cwd=\"/tmp/repo\"}
"""

    assert extract_key_learnings(markdown) == [
        "ADR slices should be implemented one at a time.",
        "Guard maturity must start warn before block.",
    ]


def test_key_learning_records_feed_governed_self_improvement(tmp_path: Path) -> None:
    markdown = """## Key Learnings:

1. New block-mode guards must include false-positive tests before promotion.
"""
    records = build_records(markdown, source="unit-test", session_id="s1")
    out = tmp_path / ".cognitive-os" / "metrics" / "key-learnings.jsonl"
    out.parent.mkdir(parents=True)
    out.write_text("".join(json.dumps(record) + "\n" for record in records), encoding="utf-8")

    signals = suggest_improvement_signals(tmp_path)

    assert len(signals) == 1
    assert signals[0].signal_type == "key_learning_candidate"
    assert signals[0].recommended_artifact == "test"
    assert "false-positive tests" in signals[0].summary


def test_key_learning_capture_cli_writes_jsonl(tmp_path: Path) -> None:
    markdown = """## Key Learnings:

1. A repeated workflow should become a skill.
"""
    result = subprocess.run(
        [str(SCRIPT), "--project-dir", str(tmp_path), "--source", "cli-test", "--json"],
        cwd=REPO,
        input=markdown,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["records"] == 1
    metrics = tmp_path / ".cognitive-os" / "metrics" / "key-learnings.jsonl"
    row = json.loads(metrics.read_text(encoding="utf-8").splitlines()[0])
    assert row["recommended_artifact"] == "skill"
