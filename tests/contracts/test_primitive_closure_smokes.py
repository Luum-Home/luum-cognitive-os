from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _run_json(script: str) -> dict[str, object]:
    result = subprocess.run(
        [str(REPO_ROOT / "scripts" / script), "--json", "--no-write"],
        cwd=str(REPO_ROOT),
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    return json.loads(result.stdout)


def test_opencode_native_plugin_smoke_proves_signed_subset() -> None:
    report = _run_json("cos-opencode-primitive-adapter-smoke")
    assert report["schema_version"] == "opencode-primitive-adapter-smoke.v1"
    assert report["status"] == "pass"
    assert report["checks"]["plugin_loaded"] is True
    assert report["checks"]["all_signed_outcomes_passed"] is True
    assert report["checks"]["all_signed_ledger_rows_present"] is True
    assert report["checks"]["content_free_rows"] is True
    assert len(report["supported_primitives"]) >= 20
    assert {
        "destructive-git-blocker",
        "destructive-rm-blocker",
        "large-file-advisor",
        "skill-router",
        "reinvention-check",
        "dispatch-gate",
    } <= set(report["supported_primitives"])


def test_portable_ai_consumer_smoke_installs_overlay_without_canonical_mutation() -> None:
    report = _run_json("cos-portable-ai-consumer-smoke")
    assert report["schema_version"] == "portable-ai-consumer-smoke.v1"
    assert report["status"] == "pass"
    assert report["registry_backed_count"] >= 307
    assert report["lifecycle_derived_count"] == 0
    assert report["no_canonical_mutation"] is True


def test_service_headless_smoke_proves_content_free_runtime_ledger() -> None:
    report = _run_json("cos-primitive-service-headless-smoke")
    assert report["schema_version"] == "primitive-service-headless-smoke.v1"
    assert report["status"] == "pass"
    assert report["content_free_rows"] is True
    assert {"destructive-git-blocker", "destructive-rm-blocker", "skill-router", "large-file-advisor", "reinvention-check"} <= set(report["primitive_ids"])
