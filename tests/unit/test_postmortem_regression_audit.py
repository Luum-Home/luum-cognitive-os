from __future__ import annotations

import json
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "cos-postmortem-regression-audit"


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run_audit(root: Path) -> dict:
    proc = subprocess.run(["python3", str(SCRIPT), "--project-dir", str(root), "--json"], text=True, capture_output=True, check=False)
    assert proc.stdout, proc.stderr
    payload = json.loads(proc.stdout)
    payload["returncode"] = proc.returncode
    return payload


def test_detects_direct_filter_repo_callsite(tmp_path: Path) -> None:
    write(tmp_path / "lib" / "history_sanitization.py", "cmd = ['git', 'filter-repo']\n")
    payload = run_audit(tmp_path)
    assert any(f["code"] == "direct-filter-repo-callsite" for f in payload["findings"])


def test_detects_missing_post_rewrite_marker_support(tmp_path: Path) -> None:
    write(tmp_path / "scripts" / "push_collision_detect.py", "print('collision')\n")
    write(tmp_path / "hooks" / "_lib" / "push-collision-check.sh", "echo check\n")
    payload = run_audit(tmp_path)
    assert any(f["code"] == "post-rewrite-push-exception-missing" for f in payload["findings"])


def test_detects_claim_enforcer_missing_tests(tmp_path: Path) -> None:
    write(tmp_path / "hooks" / "claim-validator.sh", "echo 'warning only (not blocking)'\n")
    write(tmp_path / "rules" / "trust-score.md", "TRUST_REPORT docs\n")
    payload = run_audit(tmp_path)
    codes = {f["code"] for f in payload["findings"]}
    assert "claim-enforcer-behavior-tests-missing" in codes
    assert "claim-validator-advisory-language-present" in codes


def test_detects_chaos_protected_source_write(tmp_path: Path) -> None:
    write(tmp_path / "tests" / "chaos" / "test_bad.py", "Path('lib/targeted_test_resolver.py').write_text('x')\n")
    payload = run_audit(tmp_path)
    assert any(f["code"] == "chaos-test-writes-protected-source" for f in payload["findings"])
    assert any(f["code"] == "chaos-readonly-fixture-missing" for f in payload["findings"])


def test_detects_release_freeze_missing_artifacts(tmp_path: Path) -> None:
    payload = run_audit(tmp_path)
    assert any(f["code"] == "release-freeze-artifact-missing" for f in payload["findings"])
