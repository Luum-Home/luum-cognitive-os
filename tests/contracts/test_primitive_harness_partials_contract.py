from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "primitive_harness_partials.py"
REPORT = REPO / "docs" / "reports" / "primitive-harness-partials-latest.json"
MARKDOWN = REPO / "docs" / "reports" / "primitive-harness-partials-latest.md"


def test_repository_partials_report_regenerates_with_priority_order() -> None:
    subprocess.run(
        ["python3", str(REPO / "scripts" / "primitive_harness_coverage.py"), "--project-dir", str(REPO)],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=True,
        timeout=120,
    )
    result = subprocess.run(
        ["python3", str(SCRIPT), "--project-dir", str(REPO)],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    payload = json.loads(REPORT.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "primitive-harness-partials.v1"
    assert payload["summary"]["unclassified_gaps"] == 0
    assert set(payload["summary"]["by_policy"]).issubset({"must-fix-parity", "codex-adapter-needed", "projectable-needs-driver", "behavior-proof-needed", "unclassified"})
    assert "Primitive Harness Partials" in MARKDOWN.read_text(encoding="utf-8")


def test_resolved_top_ten_codex_adapter_gaps_are_no_longer_partial() -> None:
    if not REPORT.exists():
        subprocess.run(["python3", str(SCRIPT), "--project-dir", str(REPO)], cwd=REPO, check=True, timeout=120)
    coverage = json.loads((REPO / "docs" / "reports" / "primitive-harness-coverage-latest.json").read_text(encoding="utf-8"))
    rows = {row["primitive"]: row for row in coverage["items"]}
    resolved = {
        "hooks/adaptive-bypass.sh",
        "hooks/adr-detector.sh",
        "hooks/agent-bus-monitor.sh",
        "hooks/agent-checkpoint.sh",
        "hooks/agent-output-verifier.sh",
        "hooks/agent-prelaunch.sh",
        "hooks/agent-quota-advisor.sh",
        "hooks/agent-qwen-bridge.sh",
        "hooks/agent-working-dir-inject.sh",
        "hooks/aguara-scan.sh",
    }
    for primitive in resolved:
        assert rows[primitive].get("gap_status") in {None, "aligned"}
        assert rows[primitive].get("gap_policy") != "codex-adapter-needed"


def test_resolved_second_codex_adapter_gap_batch_is_no_longer_partial() -> None:
    coverage = json.loads((REPO / "docs" / "reports" / "primitive-harness-coverage-latest.json").read_text(encoding="utf-8"))
    rows = {row["primitive"]: row for row in coverage["items"]}
    resolved = {
        "hooks/architecture-compliance.sh",
        "hooks/assumption-tracker.sh",
        "hooks/auto-checkpoint.sh",
        "hooks/auto-refine.sh",
        "hooks/auto-repair-dispatcher.sh",
        "hooks/auto-rollback-trigger.sh",
        "hooks/auto-verify.sh",
        "hooks/background-agent-reminder.sh",
        "hooks/blast-radius.sh",
        "hooks/claim-validator.sh",
    }
    for primitive in resolved:
        assert rows[primitive].get("gap_status") in {None, "aligned"}
        assert rows[primitive].get("gap_policy") != "codex-adapter-needed"
