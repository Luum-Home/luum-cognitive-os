from __future__ import annotations

import json
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "cos-postmortem-regression-audit"


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run_audit(root: Path, manifest: Path) -> dict:
    proc = subprocess.run(
        ["python3", str(SCRIPT), "--project-dir", str(root), "--manifest", str(manifest), "--json"],
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.stdout, proc.stderr
    payload = json.loads(proc.stdout)
    payload["returncode"] = proc.returncode
    return payload


def test_manifest_required_paths_check_detects_missing_artifact(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.yaml"
    write(manifest, """schema_version: postmortem-regression-audit/v1
checks:
  - id: missing-wrapper
    adr: ADR-242
    type: required_paths
    severity: block
    message: missing wrapper
    paths: [scripts/cos-filter-repo-wrap.sh]
""")
    payload = run_audit(tmp_path, manifest)
    assert payload["status"] == "block"
    assert any(f["code"] == "missing-wrapper" for f in payload["findings"])


def test_manifest_forbidden_pattern_check_detects_direct_filter_repo_callsite(tmp_path: Path) -> None:
    write(tmp_path / "lib" / "history_sanitization.py", "cmd = ['git', 'filter-repo']\n")
    manifest = tmp_path / "manifest.yaml"
    write(manifest, r"""schema_version: postmortem-regression-audit/v1
checks:
  - id: direct-filter-repo-callsite
    adr: ADR-242
    type: forbidden_pattern
    severity: block
    message: direct call
    scope: [lib]
    suffixes: [.py]
    pattern: >-
      \[\s*['"]git['"]\s*,\s*['"]filter-repo['"]
""")
    payload = run_audit(tmp_path, manifest)
    assert any(f["code"] == "direct-filter-repo-callsite" for f in payload["findings"])


def test_manifest_required_tokens_check_reports_missing_tokens(tmp_path: Path) -> None:
    write(tmp_path / "scripts" / "push_collision_detect.py", "print('collision')\n")
    manifest = tmp_path / "manifest.yaml"
    write(manifest, """schema_version: postmortem-regression-audit/v1
checks:
  - id: marker-missing
    adr: ADR-243
    type: required_tokens
    severity: block
    message: marker support missing
    files: [scripts/push_collision_detect.py]
    tokens: [last-rewrite.json, pre_head]
""")
    payload = run_audit(tmp_path, manifest)
    finding = next(f for f in payload["findings"] if f["code"] == "marker-missing")
    assert finding["details"]["missing_tokens"] == ["last-rewrite.json", "pre_head"]


def test_manifest_forbidden_line_pair_detects_chaos_protected_source_write(tmp_path: Path) -> None:
    write(tmp_path / "tests" / "chaos" / "test_bad.py", "Path('lib/targeted_test_resolver.py').write_text('x')\n")
    manifest = tmp_path / "manifest.yaml"
    write(manifest, r"""schema_version: postmortem-regression-audit/v1
checks:
  - id: chaos-test-writes-protected-source
    adr: ADR-245
    type: forbidden_line_pair
    severity: block
    message: protected write
    scope: [tests/chaos]
    suffixes: [.py]
    line_pattern: "write_text"
    same_line_pattern: "(?:lib|scripts|hooks)/[A-Za-z0-9_./-]+"
""")
    payload = run_audit(tmp_path, manifest)
    assert any(f["code"] == "chaos-test-writes-protected-source" for f in payload["findings"])


def test_external_tool_adapter_contract_requires_boundary_fields(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.yaml"
    write(manifest, """schema_version: postmortem-regression-audit/v1
checks: []
external_tools:
  - tool: gitleaks
    owner: release-secret-audit
""")
    payload = run_audit(tmp_path, manifest)
    assert any(f["code"] == "external-tool-adapter-contract-incomplete" for f in payload["findings"])
