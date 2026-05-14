from __future__ import annotations

import json
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "primitive-coherence-audit.py"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _run(repo: Path, manifest: Path) -> dict:
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


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "--initial-branch=main"], cwd=repo, check=True, stdout=subprocess.DEVNULL)
    return repo


def test_blocks_mutating_snapshot_before_preflight(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _write(repo / ".claude" / "settings.json", '''{
      "hooks": {"PreToolUse": [{"matcher": "Agent", "hooks": [
        {"command": "bash hooks/pre-agent-snapshot.sh"},
        {"command": "bash hooks/agent-prelaunch.sh"}
      ]}]}
    }''')
    manifest = repo / "manifests" / "primitive-coherence.yaml"
    _write(manifest, '''schema_version: primitive-coherence/v1
surfaces: []
ordering_constraints:
  - id: agent-prelaunch-before-snapshot
    event: PreToolUse
    matcher: Agent
    after: hooks/agent-prelaunch.sh
    before: hooks/pre-agent-snapshot.sh
    severity: block
''')

    payload = _run(repo, manifest)

    assert payload["status"] == "block"
    assert payload["returncode"] == 1
    assert any(f["code"] == "ordering-mutator-before-blocker" for f in payload["findings"])


def test_warns_when_legacy_registration_checker_ignores_opt_in_classification(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _write(repo / ".claude" / "settings.json", '{"hooks": {}}')
    _write(repo / "scripts" / "check_hook_registration.py", '''#!/usr/bin/env python3
print("UNREGISTERED hooks (1):")
print("  - session-end-cleanup.sh  (missing: settings_json)")
''')
    (repo / "scripts" / "check_hook_registration.py").chmod(0o755)
    _write(repo / "manifests" / "hook-registration-classification.yaml", '''entries:
  - path: hooks/session-end-cleanup.sh
    status: opt_in
    rationale: intentionally optional
    next_action: keep opt-in
''')
    manifest = repo / "manifests" / "primitive-coherence.yaml"
    _write(manifest, '''schema_version: primitive-coherence/v1
registration:
  classification_manifest: manifests/hook-registration-classification.yaml
  legacy_checker: scripts/check_hook_registration.py
  intentional_absent_statuses: [opt_in, manual_trigger, future]
surfaces: []
ordering_constraints: []
''')

    payload = _run(repo, manifest)

    assert payload["status"] == "warn"
    assert payload["returncode"] == 0
    assert any(f["code"] == "registration-checker-classification-disagreement" for f in payload["findings"])


def test_blocks_multi_writer_surface_without_allowance(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _write(repo / ".claude" / "settings.json", '{"hooks": {}}')
    manifest = repo / "manifests" / "primitive-coherence.yaml"
    _write(manifest, '''schema_version: primitive-coherence/v1
surfaces:
  - id: git.branch_context
    owner: git-control-plane
    allowed_multi_writer: false
    writers:
      - hooks/a.sh
      - hooks/b.sh
ordering_constraints: []
''')

    payload = _run(repo, manifest)

    assert payload["status"] == "block"
    assert any(f["code"] == "surface-multi-writer-without-allowance" for f in payload["findings"])
    assert any(f["code"] == "surface-multi-writer-without-protocol" for f in payload["findings"])


def test_blocks_unclassified_unregistered_hook(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _write(repo / ".claude" / "settings.json", '{"hooks": {}}')
    _write(repo / "scripts" / "check_hook_registration.py", '''#!/usr/bin/env python3
print("UNREGISTERED hooks (1):")
print("  - mystery-hook.sh  (missing: settings_json)")
''')
    (repo / "scripts" / "check_hook_registration.py").chmod(0o755)
    _write(repo / "manifests" / "hook-registration-classification.yaml", 'entries: []\n')
    manifest = repo / "manifests" / "primitive-coherence.yaml"
    _write(manifest, '''schema_version: primitive-coherence/v1
registration:
  classification_manifest: manifests/hook-registration-classification.yaml
  legacy_checker: scripts/check_hook_registration.py
  intentional_absent_statuses: [opt_in, manual_trigger, future]
surfaces: []
ordering_constraints: []
''')

    payload = _run(repo, manifest)

    assert payload["status"] == "block"
    assert payload["returncode"] == 1
    assert any(f["code"] == "unclassified-unregistered-hook" for f in payload["findings"])


def test_current_repo_audit_is_read_only_and_machine_readable() -> None:
    proc = subprocess.run(
        ["python3", str(SCRIPT), "--project-dir", str(SCRIPT.parents[1]), "--json"],
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.stdout, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["schema_version"] == "primitive-coherence-audit/v1"
    assert payload["policy"] == "Read-only. Detect contradictions; do not auto-repair primitives."
    assert "findings" in payload


def test_blocks_declared_primitive_recursion_cycle(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _write(repo / ".claude" / "settings.json", '{"hooks": {}}')
    manifest = repo / "manifests" / "primitive-coherence.yaml"
    _write(manifest, '''schema_version: primitive-coherence/v1
surfaces: []
ordering_constraints: []
primitive_edges:
  - from: hooks/a.sh
    to: scripts/b.py
  - from: scripts/b.py
    to: hooks/a.sh
''')

    payload = _run(repo, manifest)

    assert payload["status"] == "block"
    assert any(f["code"] == "primitive-recursion-cycle" for f in payload["findings"])


def test_blocks_incomplete_external_tool_boundary(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _write(repo / ".claude" / "settings.json", '{"hooks": {}}')
    manifest = repo / "manifests" / "primitive-coherence.yaml"
    _write(manifest, '''schema_version: primitive-coherence/v1
surfaces: []
ordering_constraints: []
external_tool_boundaries:
  - tool: trivy
    owner: supply-chain-audit
    license_spdx: Apache-2.0
''')

    payload = _run(repo, manifest)

    assert payload["status"] == "block"
    assert any(f["code"] == "external-tool-boundary-incomplete" for f in payload["findings"])


def test_blocks_active_classification_not_registered(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _write(repo / ".claude" / "settings.json", '{"hooks": {}}')
    _write(repo / "manifests" / "hook-registration-classification.yaml", '''entries:
  - path: hooks/agent-control-inbound-guard.sh
    status: active
    rationale: must be projected
    next_action: keep active
''')
    manifest = repo / "manifests" / "primitive-coherence.yaml"
    _write(manifest, '''schema_version: primitive-coherence/v1
registration:
  classification_manifest: manifests/hook-registration-classification.yaml
  active_statuses: [active]
  must_not_be_registered_statuses: [manual_trigger, future, deprecated, demoted]
surfaces: []
ordering_constraints: []
''')

    payload = _run(repo, manifest)

    assert payload["status"] == "block"
    assert any(f["code"] == "active-hook-not-registered" for f in payload["findings"])


def test_dispatcher_route_satisfies_active_classification(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _write(repo / ".claude" / "settings.json", '''{
      "hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [
        {"command": "bash hooks/bash-hot-path-dispatcher.sh"}
      ]}]}
    }''')
    _write(repo / "hooks" / "bash-hot-path-dispatcher.sh", '''#!/usr/bin/env bash
_run_gate "hooks/orchestrator-skill-invocation-gate.sh" || exit $?
''')
    _write(repo / "manifests" / "hook-registration-classification.yaml", '''entries:
  - path: hooks/orchestrator-skill-invocation-gate.sh
    status: active
    rationale: projected through dispatcher
    next_action: keep active
''')
    manifest = repo / "manifests" / "primitive-coherence.yaml"
    _write(manifest, '''schema_version: primitive-coherence/v1
registration:
  classification_manifest: manifests/hook-registration-classification.yaml
  active_statuses: [active]
  must_not_be_registered_statuses: [manual_trigger, future, deprecated, demoted]
surfaces: []
ordering_constraints: []
''')

    payload = _run(repo, manifest)

    assert payload["status"] == "pass"
    assert not payload["findings"]


def test_blocks_manual_trigger_registered_in_settings(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _write(repo / ".claude" / "settings.json", '''{
      "hooks": {"Stop": [{"matcher": "", "hooks": [
        {"command": "bash hooks/state-retention-audit.sh"}
      ]}]}
    }''')
    _write(repo / "manifests" / "hook-registration-classification.yaml", '''entries:
  - path: hooks/state-retention-audit.sh
    status: manual_trigger
    rationale: explicit operator only
    next_action: keep manual
''')
    manifest = repo / "manifests" / "primitive-coherence.yaml"
    _write(manifest, '''schema_version: primitive-coherence/v1
registration:
  classification_manifest: manifests/hook-registration-classification.yaml
  active_statuses: [active]
  must_not_be_registered_statuses: [manual_trigger, future, deprecated, demoted]
surfaces: []
ordering_constraints: []
''')

    payload = _run(repo, manifest)

    assert payload["status"] == "block"
    assert any(f["code"] == "inactive-hook-registered" for f in payload["findings"])
