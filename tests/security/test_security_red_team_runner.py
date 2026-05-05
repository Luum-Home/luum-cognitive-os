"""Security-red-team primitive tests."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import yaml

from scripts.security_red_team import build_report, render_markdown

REPO = Path(__file__).resolve().parents[2]


def test_build_report_contains_required_sections() -> None:
    report = build_report()

    assert report["schema_version"] == "security-red-team-report.v1"
    assert report["surface_inventory"]
    assert report["threat_model"]
    assert report["probes"]
    assert report["primitive_scores"]
    assert isinstance(report["overall_score"], int)


def test_required_probes_are_reported() -> None:
    manifest = yaml.safe_load((REPO / "manifests" / "security-red-team.yaml").read_text(encoding="utf-8"))
    report = build_report()
    probe_ids = {probe["id"] for probe in report["probes"]}

    assert set(manifest["required_probes"]) <= probe_ids


def test_runner_does_not_report_blocked_secret_file_contents() -> None:
    report = build_report()
    rendered = json.dumps(report, sort_keys=True) + render_markdown(report)

    assert "ALIBABA_QWEN_API_KEY=" not in rendered
    assert "sk-" not in rendered
    assert "BEGIN PRIVATE KEY" not in rendered


def test_credential_safe_integrity_probe_passes_current_manifest() -> None:
    report = build_report()
    probes = {probe["id"]: probe for probe in report["probes"]}

    assert probes["credential_safe_integrity"]["status"] == "PASS"


def test_cli_writes_json_and_markdown(tmp_path: Path) -> None:
    proc = subprocess.run(
        [
            "python3",
            str(REPO / "scripts" / "security_red_team.py"),
            "--out-dir",
            str(tmp_path),
            "--fail-on",
            "none",
        ],
        text=True,
        capture_output=True,
        timeout=20,
    )

    assert proc.returncode == 0, proc.stderr
    json_path = tmp_path / "security-red-team-latest.json"
    md_path = tmp_path / "security-red-team-latest.md"
    assert json_path.exists()
    assert md_path.exists()
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["primitive_scores"]
    assert "# Cognitive OS Security Red-Team Report" in md_path.read_text(encoding="utf-8")


def test_skill_and_docs_registered() -> None:
    skill = REPO / "skills" / "security-red-team" / "SKILL.md"
    docs = REPO / "docs" / "security" / "security-red-team.md"
    manifest = REPO / "manifests" / "security-red-team.yaml"

    assert skill.exists()
    assert docs.exists()
    assert manifest.exists()
    text = skill.read_text(encoding="utf-8")
    assert "/security-red-team" in text
    assert "scripts/security-red-team" in text
