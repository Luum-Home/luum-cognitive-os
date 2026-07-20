from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.contract

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "acc_pipeline.py"



@pytest.mark.timeout(90)
def test_repository_acc_pipeline_generates_report(tmp_path: Path) -> None:
    # This is a CONTRACT test: it proves the ACC pipeline executes end-to-end
    # and emits a schema-valid report. It intentionally does NOT invoke
    # --fail-new / assert new_debt == 0 — whether the repo currently carries
    # debt is a point-in-time fact about repo content, not a property of the
    # pipeline's correctness, and asserting it here made this test flip
    # between pass/fail non-deterministically as unrelated commits changed
    # debt counts. Debt-ratchet enforcement belongs in a dedicated ratchet
    # test (see test_primitive_harness_partial_ratchets.py), not here.
    #
    # Output is written to tmp_path (not the checked-in docs/07-Capabilities
    # tree) so this test neither reads nor mutates the repo's tracked report
    # snapshot.
    json_out = tmp_path / "latest.json"
    md_out = tmp_path / "latest.md"
    compact_out = tmp_path / "latest-compact.md"
    result = subprocess.run(
        [
            "python3",
            str(SCRIPT),
            "--project-dir",
            str(REPO_ROOT),
            "--json-out",
            str(json_out),
            "--md-out",
            str(md_out),
            "--compact-out",
            str(compact_out),
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=80,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    payload = json.loads(json_out.read_text())
    assert payload["schema_version"] == "acc.report.v1"
    assert payload["capabilities"]
    assert payload["mapping_statuses"] == ["aligned", "missing", "overexposed", "partial", "stale", "unverified"]
    assert "consumer_accessibility" in payload["capabilities"][0]
    assert "persistence" in payload
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
    assert compact_out.exists()
    assert "Context Diet Rule" in compact_out.read_text()


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
