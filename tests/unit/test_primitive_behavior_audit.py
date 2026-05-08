from __future__ import annotations

import json
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "primitive-behavior-audit.py"


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run_audit(repo: Path, manifest: Path) -> dict:
    proc = subprocess.run(
        ["python3", str(SCRIPT), "--project-dir", str(repo), "--manifest", str(manifest), "--json"],
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.stdout, proc.stderr
    payload = json.loads(proc.stdout)
    payload["returncode"] = proc.returncode
    return payload


def test_passes_when_contract_has_falsification_and_fail_closed_evidence(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    write(
        repo / "tests" / "behavior" / "test_gate.py",
        """
def test_blocks_branch_switch():
    command = "git switch risky-branch"
    result = run_hook(command)
    assert result.returncode == 1
    assert "BLOCKED" in result.stderr


def test_bypass_is_explicit():
    assert "COS_ALLOW_BRANCH_SWITCH"
""",
    )
    manifest = repo / "manifest.yaml"
    write(
        manifest,
        """
schema_version: primitive-behavior-contracts/v1
contracts:
  - id: branch-switch
    criticality: high
    proof_tests:
      - tests/behavior/test_gate.py
    required_evidence:
      - id: switch-probe
        patterns: ['git switch']
      - id: fail-closed
        patterns: ['returncode\\s*==\\s*1', 'BLOCKED']
      - id: bypass
        patterns: ['COS_ALLOW_BRANCH_SWITCH']
""",
    )

    payload = run_audit(repo, manifest)

    assert payload["status"] == "pass"
    assert payload["returncode"] == 0
    assert payload["summary"]["findings"] == 0


def test_blocks_missing_declared_proof_file(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    manifest = repo / "manifest.yaml"
    write(
        manifest,
        """
schema_version: primitive-behavior-contracts/v1
contracts:
  - id: missing-proof
    criticality: high
    proof_tests:
      - tests/behavior/test_missing.py
    required_evidence:
      - id: probe
        patterns: ['git switch']
""",
    )

    payload = run_audit(repo, manifest)

    assert payload["status"] == "block"
    assert payload["returncode"] == 1
    assert any(f["code"] == "proof-test-file-missing" for f in payload["findings"])


def test_blocks_overfit_existence_only_test_without_behavioral_evidence(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    write(
        repo / "tests" / "audit" / "test_hook_exists.py",
        """
from pathlib import Path

def test_hook_exists():
    assert Path('hooks/destructive-git-blocker.sh').exists()
""",
    )
    manifest = repo / "manifest.yaml"
    write(
        manifest,
        """
schema_version: primitive-behavior-contracts/v1
contracts:
  - id: branch-switch
    criticality: high
    proof_tests:
      - tests/audit/test_hook_exists.py
    required_evidence:
      - id: switch-probe
        patterns: ['git switch']
      - id: fail-closed
        patterns: ['returncode\\s*==\\s*[12]']
""",
    )

    payload = run_audit(repo, manifest)

    codes = [f["code"] for f in payload["findings"]]
    assert payload["status"] == "block"
    assert "behavioral-evidence-missing" in codes
    assert "fail-closed-proof-absent" in codes
    assert "proof-test-overfit-smell" in codes


def test_supports_any_match_for_alternative_falsification_phrasing(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    write(
        repo / "tests" / "behavior" / "test_gate.py",
        """
def test_blocks():
    payload = {"status": "block"}
    assert payload["status"] == "block"
""",
    )
    manifest = repo / "manifest.yaml"
    write(
        manifest,
        """
schema_version: primitive-behavior-contracts/v1
contracts:
  - id: status-blocker
    criticality: high
    proof_tests:
      - tests/behavior/test_gate.py
    required_evidence:
      - id: failure-signal
        match: any
        patterns: ['returncode\\s*==\\s*1', 'status"?\\]?\\s*==\\s*["'']block']
""",
    )

    payload = run_audit(repo, manifest)

    assert payload["status"] == "pass"


def test_current_repo_behavior_audit_is_clean_and_machine_readable() -> None:
    root = SCRIPT.parents[1]
    proc = subprocess.run(
        ["python3", str(SCRIPT), "--project-dir", str(root), "--json"],
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["schema_version"] == "primitive-behavior-audit/v1"
    assert payload["status"] == "pass"
    assert payload["summary"]["contracts"] >= 5
