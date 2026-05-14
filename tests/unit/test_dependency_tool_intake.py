from __future__ import annotations

import json
import subprocess
from pathlib import Path

import yaml

from lib.dependency_profile_ratchet import evaluate, load_baseline
from lib.dependency_tool_intake import build_triage_report


def coverage_payload() -> dict:
    return {
        "schema_version": "cos-deps-coverage-audit.v1",
        "missing_from_manifest": [
            {"name": "shellcheck", "kind": "host-tool", "sources": [{"path": "hooks/x.sh", "line": 3, "source": "command-v"}]},
            {"name": "rich", "kind": "python", "sources": [{"path": "pyproject.toml", "source": "package-manifest"}]},
        ],
        "optional_lane_needed": [
            {"name": "numpy", "kind": "python", "sources": [{"path": "requirements/dependency-lanes/semantic.txt", "source": "package-manifest"}]},
        ],
        "blocked_or_removed_by_policy": [
            {"name": "langfuse", "kind": "python", "sources": [{"path": "requirements/dependency-lanes/observability.txt"}], "details": {"verdict": "REMOVE"}},
        ],
        "platform_builtin": [
            {"name": "cat", "kind": "platform-builtin", "sources": [{"path": "hooks/x.sh", "line": 4}]},
        ],
        "internal_helper_false_positive": [
            {"name": "safe_jsonl_append", "kind": "internal-helper", "sources": [{"path": "hooks/x.sh", "line": 5}]},
        ],
        "manifested_but_unused": [
            {"name": "jq", "kind": "host-tool", "sources": [{"path": "manifests/dependencies.yaml"}]},
        ],
    }


def test_triage_maps_coverage_buckets_to_safe_actions() -> None:
    report = build_triage_report(coverage_payload())
    by_name = {row["name"]: row for row in report["proposals"]}

    assert report["schema_version"] == "cos-deps-triage.v1"
    assert by_name["shellcheck"]["action"] == "triage_manifest_profile"
    assert by_name["rich"]["action"] == "triage_python_group_or_lane"
    assert by_name["numpy"]["action"] == "map_python_lane_to_manifest_profile"
    assert by_name["numpy"]["details"]["lane"] == "semantic"
    assert by_name["langfuse"]["action"] == "block_or_remove"
    assert by_name["cat"]["action"] == "keep_platform_builtin"
    assert by_name["safe_jsonl_append"]["action"] == "suppress_false_positive"
    assert by_name["jq"]["action"] == "review_unused_manifest_entry"
    assert report["summary"]["actionable"] == 4


def test_profile_ratchet_blocks_new_actionable_findings(tmp_path: Path) -> None:
    triage = build_triage_report(coverage_payload())
    accepted = {triage["proposals"][0]["fingerprint"]}

    report = evaluate(triage, accepted)

    assert report["status"] == "block"
    assert report["new_findings"] == 3


def test_profile_ratchet_baseline_loader(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline.yaml"
    baseline.write_text(yaml.safe_dump({"accepted_findings": ["a", "b"]}), encoding="utf-8")

    assert load_baseline(baseline) == {"a", "b"}


def test_triage_cli_accepts_existing_coverage_report(project_root: Path, tmp_path: Path) -> None:
    coverage = tmp_path / "coverage.json"
    coverage.write_text(json.dumps(coverage_payload()), encoding="utf-8")

    result = subprocess.run(
        [str(project_root / "scripts/cos-deps-triage"), "--coverage-report", str(coverage), "--json"],
        check=False,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    payload = json.loads(result.stdout)
    assert payload["summary"]["actionable"] == 4


def test_ratchet_cli_blocks_unaccepted_findings(project_root: Path, tmp_path: Path) -> None:
    triage = tmp_path / "triage.json"
    triage.write_text(json.dumps(build_triage_report(coverage_payload())), encoding="utf-8")
    baseline = tmp_path / "baseline.yaml"
    baseline.write_text("schema_version: dependency-coverage-baseline/v1\naccepted_findings: []\n", encoding="utf-8")

    result = subprocess.run(
        [str(project_root / "scripts/cos-deps-profile-ratchet"), "--triage-report", str(triage), "--baseline", str(baseline), "--json"],
        check=False,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 2
    payload = json.loads(result.stdout)
    assert payload["status"] == "block"
    assert payload["new_findings"] == 4
