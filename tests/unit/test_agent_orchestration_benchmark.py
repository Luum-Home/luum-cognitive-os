from __future__ import annotations

import json
import subprocess
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT_ROOT / "scripts" / "agent-orchestration-benchmark.py"
MANIFEST = PROJECT_ROOT / "manifests" / "agent-orchestration-adapters.yaml"


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run_benchmark(project: Path, manifest: Path) -> dict:
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


def test_current_agent_orchestration_benchmark_has_no_required_failures() -> None:
    payload = run_benchmark(PROJECT_ROOT, MANIFEST)

    assert payload["summary"]["required_failures"] == 0
    assert payload["status"] == "pass"
    assert payload["summary"]["fixtures"] >= 8


def test_benchmark_blocks_missing_required_behavioral_pattern(tmp_path: Path) -> None:
    write(tmp_path / "tests/evidence.py", "this file lacks the required proof\n")
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(
        yaml.safe_dump(
            {
                "schema_version": "agent-orchestration-adapters/v1",
                "policy": {"default_adapter": "local"},
                "benchmark": {
                    "fixtures": [
                        {
                            "id": "handoff-cycle-detected",
                            "required": True,
                            "evidence_tests": ["tests/evidence.py"],
                            "required_patterns": ["HandoffCycleDetected"],
                        }
                    ]
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    payload = run_benchmark(tmp_path, manifest)

    assert payload["status"] == "block"
    assert payload["summary"]["required_failures"] == 1
    assert payload["findings"][0]["code"] == "orchestration-benchmark-missing-proof"
    assert payload["findings"][0]["missing_patterns"] == ["HandoffCycleDetected"]
