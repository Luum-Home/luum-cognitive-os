from __future__ import annotations

import json
import subprocess
import shutil

import pytest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TRACKED_SMOKE_REPORTS = (
    REPO_ROOT / "docs" / "06-Daily" / "reports" / "opencode-primitive-adapter-smoke-latest.json",
    REPO_ROOT / "docs" / "06-Daily" / "reports" / "opencode-primitive-adapter-smoke-latest.md",
    REPO_ROOT / "docs" / "06-Daily" / "reports" / "portable-ai-consumer-smoke-latest.json",
    REPO_ROOT / "docs" / "06-Daily" / "reports" / "portable-ai-consumer-smoke-latest.md",
    REPO_ROOT / "docs" / "06-Daily" / "reports" / "portable-ai-real-consumer-smoke-latest.json",
    REPO_ROOT / "docs" / "06-Daily" / "reports" / "portable-ai-real-consumer-smoke-latest.md",
    REPO_ROOT / "docs" / "06-Daily" / "reports" / "primitive-service-headless-smoke-latest.json",
    REPO_ROOT / "docs" / "06-Daily" / "reports" / "primitive-service-headless-smoke-latest.md",
)


def _report_snapshot() -> dict[Path, str]:
    return {path: path.read_text(encoding="utf-8") for path in TRACKED_SMOKE_REPORTS}


def _run_json(script: str) -> dict[str, object]:
    before = _report_snapshot()
    result = subprocess.run(
        [str(REPO_ROOT / "scripts" / script), "--json", "--check"],
        cwd=str(REPO_ROOT),
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    assert _report_snapshot() == before, f"{script} --check dirtied tracked smoke reports"
    return json.loads(result.stdout)


def test_opencode_native_plugin_smoke_proves_signed_subset() -> None:
    if shutil.which("opencode") is None:
        pytest.skip("opencode binary is optional for laptop contract lane")
    report = _run_json("cos-opencode-primitive-adapter-smoke")
    assert report["schema_version"] == "opencode-primitive-adapter-smoke.v1"
    assert report["status"] == "pass"
    assert report["checks"]["plugin_loaded"] is True
    assert report["checks"]["all_signed_outcomes_passed"] is True
    assert report["checks"]["all_signed_ledger_rows_present"] is True
    assert report["checks"]["content_free_rows"] is True
    assert len(report["supported_primitives"]) >= 30
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
    assert report["lifecycle_derived_count"] >= 0
    assert report["no_canonical_mutation"] is True


def test_service_headless_smoke_proves_content_free_runtime_ledger() -> None:
    report = _run_json("cos-primitive-service-headless-smoke")
    assert report["schema_version"] == "primitive-service-headless-smoke.v1"
    assert report["status"] == "pass"
    assert report["content_free_rows"] is True
    assert {"destructive-git-blocker", "destructive-rm-blocker", "skill-router", "large-file-advisor", "reinvention-check"} <= set(report["primitive_ids"])


def test_portable_ai_real_consumer_smoke_uses_registered_consumer_shadows() -> None:
    report = _run_json("cos-portable-ai-real-consumer-smoke")
    assert report["schema_version"] == "portable-ai-real-consumer-smoke.v1"
    assert report["status"] in {"pass", "warn"}
    assert report["decision"]["mutates_real_consumers"] is False
    if report["tested_consumer_count"]:
        assert report["passing_consumer_count"] == report["tested_consumer_count"]
        assert all(row["actual_consumer_unchanged"] for row in report["consumer_rows"])
