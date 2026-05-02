from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "cos_primitive_harvester.py"


def test_harvester_runs_against_consumer_repo_with_no_primitives(tmp_path: Path) -> None:
    consumer = tmp_path / "consumer"
    consumer.mkdir()
    (consumer / "README.md").write_text("consumer\n", encoding="utf-8")

    result = subprocess.run(
        [
            "python3",
            str(SCRIPT),
            "--repo",
            str(consumer),
            "--text",
            "Esto debería ser automático: script reusable con tests y checklist para validar cleanup.",
            "--json",
        ],
        text=True,
        capture_output=True,
        check=True,
        timeout=30,
    )
    payload = json.loads(result.stdout)

    assert payload["decision"] == "CREATE_PRIMITIVE"
    assert payload["artifact_plan"]


def test_harvester_rejects_missing_input(tmp_path: Path) -> None:
    result = subprocess.run(
        ["python3", str(SCRIPT), "--repo", str(tmp_path), "--json"],
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )

    assert result.returncode != 0
    assert "Provide --text or --conversation-file" in result.stderr
