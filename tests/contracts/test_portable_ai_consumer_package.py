"""Human-readable consumer `.ai` package contracts."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from scripts.portable_ai_consumer_package import build_package, build_report
from scripts.portable_ai_overlay import build_overlay

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_consumer_package_is_markdown_only_and_complete() -> None:
    package = build_package(REPO_ROOT)
    overlay = build_overlay(REPO_ROOT)

    primitive_overlay_count = sum(1 for path in overlay if path.startswith("primitives/") and path.endswith(".json"))
    adapter_overlay_count = sum(1 for path in overlay if path.startswith("adapters/") and path.endswith("/adapter.json"))
    primitive_markdown_count = sum(1 for path in package if path.startswith("primitives/") and path.endswith(".md") and path != "primitives/INDEX.md")
    adapter_markdown_count = sum(1 for path in package if path.startswith("adapters/") and path.endswith(".md") and path != "adapters/INDEX.md")

    assert "README.md" in package
    assert "context/overview.md" in package
    assert "primitives/INDEX.md" in package
    assert "adapters/INDEX.md" in package
    assert primitive_markdown_count == primitive_overlay_count
    assert adapter_markdown_count == adapter_overlay_count
    assert not any(path.endswith(".json") for path in package)
    assert all(body.startswith("---\n") for body in package.values())
    assert "structural-advisory" in package["adapters/agents-md.md"]
    assert "Skill rows excluded" in package["context/overview.md"]


def test_consumer_package_smoke_proves_tempdir_no_mutation() -> None:
    report = build_report(REPO_ROOT)

    assert report["schema_version"] == "portable-ai-consumer-package-smoke.v1"
    assert report["status"] == "pass"
    assert report["json_file_count"] == 0
    assert report["primitive_markdown_count"] == report["primitive_overlay_count"]
    assert report["adapter_markdown_count"] == report["adapter_overlay_count"]
    assert report["no_canonical_mutation"] is True


def test_consumer_package_smoke_cli_check_is_non_mutating() -> None:
    latest = REPO_ROOT / "docs" / "06-Daily" / "reports" / "portable-ai-consumer-package-smoke-latest.json"
    before = latest.read_text(encoding="utf-8") if latest.exists() else None
    result = subprocess.run(
        [str(REPO_ROOT / "scripts" / "cos-portable-ai-consumer-package-smoke"), "--check", "--json"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=60,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "pass"
    after = latest.read_text(encoding="utf-8") if latest.exists() else None
    assert after == before
