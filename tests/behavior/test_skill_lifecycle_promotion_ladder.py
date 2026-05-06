"""Behavior coverage for ADR-177 skill lifecycle promotion ladder."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT_ROOT / "scripts" / "cos-doctrine-proposer"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def test_doctrine_proposer_writes_skill_lifecycle_proposal_without_promoting(tmp_path: Path) -> None:
    skill = tmp_path / ".cognitive-os" / "skills" / "auto-generated" / "useful-sandbox" / "SKILL.md"
    _write(
        skill,
        """---
name: useful-sandbox
auto-generated: true
status: sandbox
---
# Useful sandbox
""",
    )

    _write(tmp_path / ".claude" / "settings.json", json.dumps({"hooks": {}}))
    _write(tmp_path / "manifests" / "primitive-lifecycle.yaml", "schema_version: 1\nprimitives: []\n")
    _write(tmp_path / "manifests" / "external-adoption-evidence.yaml", "schema_version: 1\nevidence: []\n")

    _write_jsonl(
        tmp_path / ".cognitive-os" / "metrics" / "skill-invocations.jsonl",
        [
            {"timestamp": "2026-05-05T10:00:00+00:00", "payload": {"skill_name": "useful-sandbox"}}
            for _ in range(50)
        ],
    )
    _write_jsonl(
        tmp_path / ".cognitive-os" / "metrics" / "skill-feedback.jsonl",
        [{"timestamp": "2026-05-05T10:01:00Z", "skill": "useful-sandbox", "success": True} for _ in range(5)],
    )

    result = subprocess.run(
        [str(SCRIPT), "--project-dir", str(tmp_path), "--profile", "core", "--write", "--json"],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "proposals_available"
    assert any(p["proposal_id"] == "activate-skill-lifecycle-promotion-ladder" for p in payload["proposals"])
    written = Path(payload["written_to"])
    assert written.parent == tmp_path / "docs" / "proposals"
    markdown = written.read_text(encoding="utf-8")
    assert "runtime_effect: none" in markdown
    assert "useful-sandbox" in markdown
    assert skill.exists()
    assert not (tmp_path / ".cognitive-os" / "skills" / "cos" / "useful-sandbox" / "SKILL.md").exists()

    log_path = tmp_path / ".cognitive-os" / "metrics" / "lifecycle-promotion-proposals.jsonl"
    assert "activate-skill-lifecycle-promotion-ladder" in log_path.read_text(encoding="utf-8")
