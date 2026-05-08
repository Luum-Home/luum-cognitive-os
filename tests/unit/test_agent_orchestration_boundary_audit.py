from __future__ import annotations

import json
import subprocess
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT_ROOT / "scripts" / "agent-orchestration-boundary-audit.py"
MANIFEST = PROJECT_ROOT / "manifests" / "agent-orchestration-adapters.yaml"


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run_audit(project: Path, manifest: Path) -> dict:
    proc = subprocess.run(
        ["python3", str(SCRIPT), "--project-dir", str(project), "--manifest", str(manifest), "--json"],
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.stdout, proc.stderr
    payload = json.loads(proc.stdout)
    payload["returncode"] = proc.returncode
    return payload


def test_current_agent_orchestration_boundary_manifest_passes() -> None:
    payload = run_audit(PROJECT_ROOT, MANIFEST)

    assert payload["status"] == "pass"
    assert payload["summary"]["block"] == 0
    assert payload["summary"]["adapters"] >= 4
    assert payload["summary"]["surfaces"] >= 5


def test_audit_blocks_direct_optional_framework_import_in_core(tmp_path: Path) -> None:
    write(tmp_path / "lib/agent_runtime.py", "import langgraph\n")
    write(tmp_path / "tests/evidence.py", "handoff-cycle-detected\n")
    write(tmp_path / "scripts/bench.py", "")
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(
        yaml.safe_dump(
            {
                "schema_version": "agent-orchestration-adapters/v1",
                "policy": {
                    "default_adapter": "local",
                    "cos_owns": ["policy"],
                    "launch_paths_must_pass": ["ADR-223"],
                    "handoff_paths_must_pass": ["ADR-230"],
                    "provider_calls_must_pass": ["ADR-228"],
                },
                "forbidden_core_imports": [{"module": "langgraph", "rationale": "adapter only"}],
                "adapters": [
                    {
                        "id": "local",
                        "status": "active",
                        "default": True,
                        "implementation": "lib/agent_runtime.py",
                        "license_spdx": "project",
                        "footprint": "zero",
                        "hot_path_allowed": True,
                        "community_pattern": "local",
                        "benchmark_required": True,
                    }
                ],
                "core_surfaces": [
                    {
                        "id": "runtime",
                        "owner_adr": "ADR-X",
                        "kind": "launch_boundary",
                        "implementations": ["lib/agent_runtime.py"],
                        "required_tests": ["tests/evidence.py"],
                        "required_receipts": ["receipt"],
                    }
                ],
                "core_file_allowlist": ["lib/agent_runtime.py"],
                "unmanifested_core_file_scan": {"scopes": ["lib"], "filename_regex": "agent", "allowed_suffixes": [".py"]},
                "benchmark": {
                    "script": "scripts/bench.py",
                    "fixtures": [
                        {
                            "id": "write-agent-worktree-no-stash",
                            "evidence_tests": ["tests/evidence.py"],
                            "required_patterns": ["handoff-cycle-detected"],
                        },
                        {
                            "id": "handoff-cycle-detected",
                            "evidence_tests": ["tests/evidence.py"],
                            "required_patterns": ["handoff-cycle-detected"],
                        },
                        {
                            "id": "receiver-kill-mid-dispatch-receipt",
                            "evidence_tests": ["tests/evidence.py"],
                            "required_patterns": ["handoff-cycle-detected"],
                        },
                        {
                            "id": "dispatch-budget-pre-call-refusal",
                            "evidence_tests": ["tests/evidence.py"],
                            "required_patterns": ["handoff-cycle-detected"],
                        },
                        {
                            "id": "file-ipc-cross-session-flow",
                            "evidence_tests": ["tests/evidence.py"],
                            "required_patterns": ["handoff-cycle-detected"],
                        },
                    ],
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    payload = run_audit(tmp_path, manifest)

    assert payload["status"] == "block"
    assert any(f["code"] == "forbidden-core-orchestration-import" for f in payload["findings"])


def test_audit_blocks_unmanifested_orchestration_core_file(tmp_path: Path) -> None:
    write(tmp_path / "lib/agent_runtime.py", "")
    write(tmp_path / "lib/agent_daemon_v2.py", "")
    write(tmp_path / "tests/evidence.py", "handoff-cycle-detected\n")
    write(tmp_path / "scripts/bench.py", "")
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(
        yaml.safe_dump(
            {
                "schema_version": "agent-orchestration-adapters/v1",
                "policy": {
                    "default_adapter": "local",
                    "cos_owns": ["policy"],
                    "launch_paths_must_pass": ["ADR-223"],
                    "handoff_paths_must_pass": ["ADR-230"],
                    "provider_calls_must_pass": ["ADR-228"],
                },
                "forbidden_core_imports": [],
                "adapters": [
                    {
                        "id": "local",
                        "status": "active",
                        "default": True,
                        "implementation": "lib/agent_runtime.py",
                        "license_spdx": "project",
                        "footprint": "zero",
                        "hot_path_allowed": True,
                        "community_pattern": "local",
                        "benchmark_required": True,
                    }
                ],
                "core_surfaces": [
                    {
                        "id": "runtime",
                        "owner_adr": "ADR-X",
                        "kind": "launch_boundary",
                        "implementations": ["lib/agent_runtime.py"],
                        "required_tests": ["tests/evidence.py"],
                        "required_receipts": ["receipt"],
                    }
                ],
                "core_file_allowlist": ["lib/agent_runtime.py"],
                "unmanifested_core_file_scan": {"scopes": ["lib"], "filename_regex": "agent", "allowed_suffixes": [".py"]},
                "benchmark": {
                    "script": "scripts/bench.py",
                    "fixtures": [
                        {
                            "id": fixture_id,
                            "evidence_tests": ["tests/evidence.py"],
                            "required_patterns": ["handoff-cycle-detected"],
                        }
                        for fixture_id in [
                            "write-agent-worktree-no-stash",
                            "handoff-cycle-detected",
                            "receiver-kill-mid-dispatch-receipt",
                            "dispatch-budget-pre-call-refusal",
                            "file-ipc-cross-session-flow",
                        ]
                    ],
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    payload = run_audit(tmp_path, manifest)

    assert payload["status"] == "block"
    assert any(f["code"] == "unmanifested-orchestration-core-file" and f["path"] == "lib/agent_daemon_v2.py" for f in payload["findings"])
