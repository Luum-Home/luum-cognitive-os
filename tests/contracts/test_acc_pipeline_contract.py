from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.contract

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "acc_pipeline.py"
REPORT = REPO_ROOT / "docs" / "07-Capabilities" / "acc" / "latest.json"
COMPACT = REPO_ROOT / "docs" / "07-Capabilities" / "acc" / "latest-compact.md"


@pytest.mark.timeout(90)
def test_repository_acc_pipeline_generates_report() -> None:
    result = subprocess.run(
        ["python3", str(SCRIPT), "--project-dir", str(REPO_ROOT), "--fail-new"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=80,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    payload = json.loads(REPORT.read_text())
    assert payload["schema_version"] == "acc.report.v1"
    assert payload["capabilities"]
    assert payload["mapping_statuses"] == ["aligned", "missing", "overexposed", "partial", "stale", "unverified"]
    assert "consumer_accessibility" in payload["capabilities"][0]
    assert "persistence" in payload
    assert payload["new_debt"]["status"] == "pass"
    assert payload["new_debt"]["count"] == 0
    assert payload["persistence"]["engram"]["status"] in {"unavailable", "ok"}
    for adapter in ("readiness:scripts", "readiness:hooks", "readiness:skills", "readiness:rules", "readiness:templates"):
        assert payload["adapters"][adapter]["status"] == "ok"
    assert payload["adapters"]["harness_projection"]["status"] == "ok"
    assert payload["adapters"]["projection_profiles"]["status"] == "ok"
    assert payload["adapters"]["consumer_availability"]["status"] == "ok"
    assert payload["adapters"]["shell_ci_projection"]["status"] == "ok"
    assert payload["adapters"]["harness_coverage"]["status"] == "ok"
    assert payload["adapters"]["harness_coverage"]["summary"]["unclassified_gaps"] == 0
    assert payload["adapters"]["shell_ci_projection"]["summary"]["commands"] == 17
    assert payload["adapters"]["consumer_availability"]["summary"]["statuses"]["maintainer-only"] > 0
    assert payload["adapters"]["consumer_projection"]["summary"]["by_harness_profile"]["claude/default"] > 0
    assert payload["adapters"]["consumer_projection"]["summary"]["by_harness_profile"]["claude/full"] > 0
    assert payload["adapters"]["consumer_projection"]["summary"]["by_harness_profile"]["codex/default"] > 0
    assert payload["adapters"]["consumer_projection"]["summary"]["by_harness_profile"]["codex/full"] > 0
    assert payload["adapters"]["consumer_projection"]["summary"]["by_harness_profile"]["shell-ci/default"] > 0
    assert payload["adapters"]["consumer_projection"]["summary"]["by_harness_profile"]["shell-ci/full"] > 0
    assert payload["adapters"]["consumer_projection"]["summary"]["by_harness_profile"]["qwen-code/default"] > 0
    assert payload["adapters"]["consumer_projection"]["summary"]["by_harness_profile"]["qwen-code/full"] > 0
    assert payload["adapters"]["consumer_projection"]["summary"]["by_harness_profile"]["kimi-code/default"] > 0
    assert payload["adapters"]["consumer_projection"]["summary"]["by_harness_profile"]["kimi-code/full"] > 0
    for harness in ("gemini-cli", "warp", "amp-code", "jetbrains-junie", "qoder", "factory-droid", "cline", "continue-dev", "kilo-code", "zed-ai", "augment-code", "goose", "aider"):
        assert payload["adapters"]["consumer_projection"]["summary"]["by_harness_profile"][f"{harness}/default"] > 0
        assert payload["adapters"]["consumer_projection"]["summary"]["by_harness_profile"][f"{harness}/full"] > 0
    assert payload["harness_projection"]["claude"]["status"] == "implemented"
    assert payload["harness_projection"]["codex"]["status"] == "implemented"
    assert payload["harness_projection"]["cursor"]["status"] == "implemented"
    assert payload["harness_projection"]["opencode"]["status"] == "implemented"
    assert payload["harness_projection"]["vscode-copilot"]["status"] == "implemented"
    assert payload["harness_projection"]["shell-ci"]["status"] == "implemented"
    assert payload["harness_projection"]["qwen-code"]["status"] == "implemented"
    assert payload["harness_projection"]["kimi-code"]["status"] == "implemented"
    for harness in ("gemini-cli", "warp", "amp-code", "jetbrains-junie", "qoder", "factory-droid", "cline", "continue-dev", "kilo-code", "zed-ai", "augment-code", "goose", "aider"):
        assert payload["harness_projection"][harness]["status"] == "implemented"
    assert COMPACT.exists()
    assert "Context Diet Rule" in COMPACT.read_text()


def test_harness_projection_manifest_declares_named_ides() -> None:
    manifest = yaml.safe_load((REPO_ROOT / "manifests" / "harness-projection.yaml").read_text())
    ids = {item["id"] for item in manifest["harnesses"]}
    required = {
        "claude",
        "codex",
        "cursor",
        "devin",
        "vscode-copilot",
        "opencode",
        "google-antigravity",
        "qwen-code",
        "kimi-code",
        "minimax-maxclaw",
        "deepseek-provider",
        "shell-ci",
        "gemini-cli",
        "warp",
        "amp-code",
        "jetbrains-junie",
        "qoder",
        "factory-droid",
        "kiro",
        "cline",
        "continue-dev",
        "kilo-code",
        "zed-ai",
        "augment-code",
        "goose",
        "aider",
    }

    assert required <= ids
    implemented = {item["id"] for item in manifest["harnesses"] if item["status"] == "implemented"}
    assert implemented == {"claude", "codex", "cursor", "agents-md", "opencode", "vscode-copilot", "qwen-code", "kimi-code", "gemini-cli", "warp", "amp-code", "jetbrains-junie", "qoder", "factory-droid", "cline", "continue-dev", "kilo-code", "zed-ai", "augment-code", "goose", "aider", "shell-ci"}
