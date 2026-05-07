from __future__ import annotations

import json
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "test_skip_registry.py"


def write_junit(path: Path, message: str) -> None:
    path.write_text(
        f'''<?xml version="1.0" encoding="utf-8"?>
<testsuite tests="1" skipped="1">
  <testcase classname="tests.system.test_docker" name="test_stack">
    <skipped message="{message}" />
  </testcase>
</testsuite>
''',
        encoding="utf-8",
    )


def test_skip_registry_classifies_expected_dependency_skip(tmp_path: Path) -> None:
    junit = tmp_path / "junit.xml"
    out = tmp_path / "skip-summary.json"
    write_junit(junit, "Docker daemon not running")

    result = subprocess.run(
        ["python3", str(SCRIPT), "--lane", "system", "--junit", str(junit), "--json-out", str(out), "--fail-unknown"],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(out.read_text())
    assert payload["unknown_count"] == 0
    assert payload["counts_by_category"]["external-dependency"] == 1


def test_skip_registry_fails_unknown_skip_when_enforced(tmp_path: Path) -> None:
    junit = tmp_path / "junit.xml"
    write_junit(junit, "temporarily skipped because this is hard")

    result = subprocess.run(
        ["python3", str(SCRIPT), "--lane", "unit", "--junit", str(junit), "--fail-unknown"],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert '"unknown_count": 1' in result.stdout


def test_skip_registry_audit_aggregates_latest_summaries_and_flags_suspicious(tmp_path: Path) -> None:
    old_lane = tmp_path / "20260101T000000Z-tests-audit-"
    new_lane = tmp_path / "20260102T000000Z-tests-audit-"
    contract_lane = tmp_path / "20260101T000000Z-tests-contract-"
    old_lane.mkdir()
    new_lane.mkdir()
    contract_lane.mkdir()
    (old_lane / "skip-summary.json").write_text(json.dumps({
        "lane": "audit",
        "classified": [{"nodeid": "old", "reason": "old", "category": "policy-exemption", "id": "old"}],
        "unknown": [],
    }), encoding="utf-8")
    (new_lane / "skip-summary.json").write_text(json.dumps({
        "lane": "audit",
        "classified": [
            {"nodeid": "tests.audit::test_empty[NOTSET]", "reason": "got empty parameter set for (x)", "category": "optional-runtime-state", "id": "optional-profile-artifact-absent"},
            {"nodeid": "tests.audit::test_network", "reason": "requires network access", "category": "external-dependency", "id": "external-host-tool-or-library"},
        ],
        "unknown": [],
    }), encoding="utf-8")
    (contract_lane / "skip-summary.json").write_text(json.dumps({
        "lane": "contract",
        "classified": [],
        "unknown": [{"nodeid": "tests.contract::test_mystery", "reason": "mystery skip"}],
    }), encoding="utf-8")
    out = tmp_path / "audit.json"

    result = subprocess.run(
        ["python3", str(SCRIPT), "--audit-root", str(tmp_path), "--json-out", str(out)],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(out.read_text())
    assert payload["total_skips"] == 3
    assert payload["counts_by_category"] == {"external-dependency": 1, "optional-runtime-state": 1, "unknown": 1}
    assert payload["suspicious_count"] == 2
    assert {item["nodeid"] for item in payload["suspicious"]} == {
        "tests.audit::test_empty[NOTSET]",
        "tests.contract::test_mystery",
    }


def test_skip_registry_audit_can_fail_on_suspicious(tmp_path: Path) -> None:
    lane = tmp_path / "20260101T000000Z-tests-audit-"
    lane.mkdir()
    (lane / "skip-summary.json").write_text(json.dumps({
        "lane": "audit",
        "classified": [],
        "unknown": [{"nodeid": "tests.audit::test_mystery", "reason": "mystery skip"}],
    }), encoding="utf-8")

    result = subprocess.run(
        ["python3", str(SCRIPT), "--audit-root", str(tmp_path), "--fail-suspicious"],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert '"suspicious_count": 1' in result.stdout


def test_skip_registry_audit_sanitizes_repo_paths(tmp_path: Path) -> None:
    lane = tmp_path / "20260101T000000Z-tests-audit-"
    lane.mkdir()
    repo = Path.cwd()
    (lane / "skip-summary.json").write_text(json.dumps({
        "lane": "audit",
        "classified": [{
            "nodeid": f"{repo}/tests/audit/test_example.py::test_skip",
            "reason": f"requires fixture at {repo}/.cognitive-os/runtime",
            "category": "optional-runtime-state",
            "id": "optional-profile-artifact-absent",
        }],
        "unknown": [],
    }), encoding="utf-8")
    out = tmp_path / "audit.json"

    result = subprocess.run(
        ["python3", str(SCRIPT), "--audit-root", str(tmp_path), "--json-out", str(out)],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    text = out.read_text()
    assert str(repo) not in text
    assert "<repo-root>" in text
