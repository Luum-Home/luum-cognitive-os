from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.contract

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "primitive_harness_coverage.py"
REPORT = REPO / "docs" / "reports" / "primitive-harness-coverage-latest.json"


@pytest.mark.timeout(120)
def test_repository_harness_coverage_report_regenerates() -> None:
    result = subprocess.run(
        ["python3", str(SCRIPT), "--project-dir", str(REPO)],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=False,
        timeout=90,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    payload = json.loads(REPORT.read_text())
    assert payload["schema_version"] == "primitive-harness-coverage.v1"
    assert payload["summary"]["total_primitives"] > 0
    assert payload["state_semantics"] == [
        "installed",
        "projected",
        "wired",
        "executable",
        "behavior-proven",
        "observable",
        "operable",
        "json-contract",
        "exit-code-contract",
    ]
    assert {"claude", "codex", "shell-ci", "cursor", "vscode-copilot", "opencode", "cline", "aider"} <= set(payload["harnesses"])
    assert payload["summary"].get("unclassified_gaps", 0) == 0
    assert payload["summary"].get("gaps_by_policy", {}).get("behavior-proof-needed", 0) == 0
    assert payload["summary"]["harness_wired_hooks"]["claude"] >= payload["summary"]["harness_wired_hooks"]["codex"]


def test_repository_report_contains_required_example_rows() -> None:
    if not REPORT.exists():
        subprocess.run(["python3", str(SCRIPT), "--project-dir", str(REPO)], cwd=REPO, check=True, timeout=90)
    rows = {row["primitive"]: row for row in json.loads(REPORT.read_text())["items"]}
    for primitive in [
        "hooks/session-init.sh",
        "hooks/pre-compaction-flush.sh",
        "hooks/concurrent-write-guard-codex-proxy.sh",
        "rules/RULES-COMPACT.md",
        "scripts/cos-status.sh",
    ]:
        assert primitive in rows
        row = rows[primitive]
        assert row["family"] in {"hooks", "rules", "scripts", "skills", "templates"}
        assert "claude" in row["harnesses"]
        assert "codex" in row["harnesses"]
        assert "shell-ci" in row["harnesses"]
        assert "coverage" in row
        assert "surfaces" in row
        assert row["surfaces"]["cos-cli"]["surface_kind"] == "cli"
        assert row["surfaces"]["acc-report"]["surface_kind"] == "report"
        assert row["surfaces"]["dashboard"]["surface_kind"] == "ui"
        assert row["surfaces"]["tui"]["surface_kind"] == "ui"
        assert row["surfaces"]["tui"]["observable"] is True
        assert row["surfaces"]["tui"]["operable"] in {False, True}


def test_harness_coverage_primitive_has_lifecycle_and_agent_skill() -> None:
    lifecycle = yaml.safe_load((REPO / "manifests" / "primitive-lifecycle.yaml").read_text(encoding="utf-8"))
    rows = {item["id"]: item for item in lifecycle["primitives"]}
    script_row = rows.get("scripts/primitive_harness_coverage.py")
    skill_row = rows.get("skills/primitive-harness-coverage/SKILL.md")
    assert script_row is not None
    assert skill_row is not None
    assert script_row["kind"] == "script"
    assert skill_row["kind"] == "skill"
    assert "tests/unit/test_primitive_harness_coverage.py" in "\n".join(script_row["evidence_commands"])
    assert (REPO / "skills" / "primitive-harness-coverage" / "SKILL.md").is_file()


def test_dashboard_consumes_surface_coverage_report_in_observe_only_mode() -> None:
    api = (REPO / "dashboard" / "lib" / "cos-api.ts").read_text(encoding="utf-8")
    page = (REPO / "dashboard" / "app" / "page.tsx").read_text(encoding="utf-8")
    assert "primitive-harness-coverage-latest.json" in api
    assert 'mode: "observe-only"' in api
    assert "Primitive Surface Coverage" in page
    assert "getPrimitiveSurfaceCoverageSummary" in page
