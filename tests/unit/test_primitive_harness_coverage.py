from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import yaml

MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "primitive_harness_coverage.py"
spec = importlib.util.spec_from_file_location("primitive_harness_coverage", MODULE_PATH)
assert spec and spec.loader
primitive_harness_coverage = importlib.util.module_from_spec(spec)
sys.modules["primitive_harness_coverage"] = primitive_harness_coverage
spec.loader.exec_module(primitive_harness_coverage)


def make_repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "hooks").mkdir(parents=True)
    (root / "rules").mkdir(parents=True)
    (root / "scripts").mkdir(parents=True)
    (root / "skills" / "status").mkdir(parents=True)
    (root / "templates").mkdir(parents=True)
    (root / ".claude").mkdir(parents=True)
    (root / ".codex").mkdir(parents=True)
    (root / "manifests").mkdir(parents=True)
    (root / "tests").mkdir(parents=True)

    (root / "hooks" / "session-init.sh").write_text("#!/usr/bin/env bash\n# SCOPE: both\necho init\n")
    (root / "hooks" / "pre-compaction-flush.sh").write_text("#!/usr/bin/env bash\n# SCOPE: both\necho flush\n")
    (root / "hooks" / "concurrent-write-guard-codex-proxy.sh").write_text("#!/usr/bin/env bash\n# SCOPE: both\necho codex\n")
    (root / "rules" / "RULES-COMPACT.md").write_text("<!-- SCOPE: both -->\n# Rules\n")
    (root / "scripts" / "cos-status.sh").write_text("#!/usr/bin/env bash\n# SCOPE: both\necho status\n")
    (root / "skills" / "status" / "SKILL.md").write_text("<!-- SCOPE: both -->\n---\nname: status\naudience: both\n---\n")
    (root / "templates" / "prompt.md").write_text("<!-- SCOPE: project -->\n# Prompt\n")
    (root / "tests" / "test_session_init.py").write_text("def test_session_init(): assert 'hooks/session-init.sh'\n")

    (root / ".claude" / "settings.json").write_text(
        json.dumps(
            {
                "hooks": {
                    "SessionStart": [{"hooks": [{"command": "bash hooks/session-init.sh"}]}],
                    "PreCompact": [{"hooks": [{"command": "bash hooks/pre-compaction-flush.sh"}]}],
                }
            }
        )
    )
    (root / ".codex" / "hooks.json").write_text(
        json.dumps(
            {
                "SessionStart": [{"hooks": [{"command": "bash hooks/session-init.sh"}]}],
                "UserPromptSubmit": [{"hooks": [{"command": "bash hooks/concurrent-write-guard-codex-proxy.sh"}]}],
            }
        )
    )
    (root / "manifests" / "shell-ci-projection.yaml").write_text(
        yaml.safe_dump({"commands": [{"path": "scripts/cos-status.sh"}]})
    )
    return root


def rows_by_primitive(root: Path) -> dict[str, dict]:
    report = primitive_harness_coverage.build_report(root)
    return {row["primitive"]: row for row in report["items"]}


def test_harness_coverage_distinguishes_scope_from_runtime_wiring(tmp_path: Path) -> None:
    rows = rows_by_primitive(make_repo(tmp_path))

    session = rows["hooks/session-init.sh"]
    assert session["scope"] == "both"
    assert session["harnesses"]["claude"]["wired"] is True
    assert session["harnesses"]["codex"]["wired"] is True
    assert session["gap"] is None

    precompact = rows["hooks/pre-compaction-flush.sh"]
    assert precompact["scope"] == "both"
    assert precompact["harnesses"]["claude"]["events"] == ["PreCompact"]
    assert precompact["harnesses"]["codex"]["wired"] is False
    assert "scope=both" in precompact["gap"]

    codex_proxy = rows["hooks/concurrent-write-guard-codex-proxy.sh"]
    assert codex_proxy["harnesses"]["claude"]["wired"] is False
    assert codex_proxy["harnesses"]["codex"]["wired"] is True


def test_context_and_command_surfaces_are_not_misread_as_hook_parity(tmp_path: Path) -> None:
    rows = rows_by_primitive(make_repo(tmp_path))

    compact = rows["rules/RULES-COMPACT.md"]
    assert compact["harnesses"]["claude"]["projected"] is True
    assert compact["harnesses"]["codex"]["projected"] is True
    assert compact["harnesses"]["claude"]["wired"] is False

    status = rows["scripts/cos-status.sh"]
    assert status["harnesses"]["shell-ci"]["projected"] is True
    assert status["harnesses"]["shell-ci"]["commands"] == ["scripts/cos-status.sh"]
    assert status["harnesses"]["claude"]["wired"] is False


def test_cli_writes_json_and_markdown_reports(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    result = subprocess.run(
        [sys.executable, str(MODULE_PATH), "--project-dir", str(root)],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads((root / "docs" / "reports" / "primitive-harness-coverage-latest.json").read_text())
    assert payload["schema_version"] == "primitive-harness-coverage.v1"
    assert payload["state_semantics"] == ["installed", "projected", "wired", "executable", "behavior-proven"]
    assert payload["summary"]["harness_wired_hooks"]["claude"] == 2
    assert payload["summary"]["harness_wired_hooks"]["codex"] == 2
    assert "Primitive Harness Coverage" in (root / "docs" / "reports" / "primitive-harness-coverage-latest.md").read_text()
