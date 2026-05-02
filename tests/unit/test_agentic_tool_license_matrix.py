from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "agentic_tool_license_matrix.py"
spec = importlib.util.spec_from_file_location("agentic_tool_license_matrix", MODULE_PATH)
assert spec and spec.loader
agentic_tool_license_matrix = importlib.util.module_from_spec(spec)
sys.modules["agentic_tool_license_matrix"] = agentic_tool_license_matrix
spec.loader.exec_module(agentic_tool_license_matrix)


def write_manifest(path: Path, tools: list[dict[str, object]]) -> None:
    path.write_text(json.dumps({"tools": tools}), encoding="utf-8")


def tool_row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "name": "safe-tool",
        "version_ref": "v1.2.3",
        "license_spdx": "MIT",
        "install_mode": "optional-cli",
        "default_enabled": False,
        "data_sharing": "none",
        "weight": "Low",
    }
    row.update(overrides)
    return row


def test_load_manifest_accepts_required_schema(tmp_path: Path) -> None:
    manifest = tmp_path / "tools.json"
    write_manifest(manifest, [tool_row(version_ref="commit:abc123")])

    tools = agentic_tool_license_matrix.load_manifest(manifest)

    assert tools[0].name == "safe-tool"
    assert tools[0].version_ref == "commit:abc123"
    assert tools[0].license_spdx == "MIT"


def test_blocks_forbidden_license_families(tmp_path: Path) -> None:
    manifest = tmp_path / "tools.json"
    write_manifest(
        manifest,
        [
            tool_row(name="agpl", license_spdx="AGPL-3.0-only"),
            tool_row(name="sspl", license_spdx="SSPL-1.0"),
            tool_row(name="bsl", license_spdx="BSL-1.1"),
            tool_row(name="elastic", license_spdx="Elastic-License-2.0"),
            tool_row(name="commons", license_spdx="Commons-Clause"),
        ],
    )

    result = agentic_tool_license_matrix.evaluate_tools(agentic_tool_license_matrix.load_manifest(manifest), manifest)

    assert result.passed is False
    assert {finding.tool for finding in result.findings if finding.rule == "blocked-license"} == {
        "agpl",
        "sspl",
        "bsl",
        "elastic",
        "commons",
    }


def test_blocks_heavy_external_default_enabled(tmp_path: Path) -> None:
    manifest = tmp_path / "tools.json"
    write_manifest(manifest, [tool_row(name="heavy-default", weight="Very high", default_enabled=True)])

    result = agentic_tool_license_matrix.evaluate_tools(agentic_tool_license_matrix.load_manifest(manifest), manifest)

    assert result.passed is False
    assert any(finding.rule == "heavy-external-default" for finding in result.findings)


def test_allows_internal_default_policy_even_when_enabled(tmp_path: Path) -> None:
    manifest = tmp_path / "tools.json"
    write_manifest(
        manifest,
        [tool_row(name="internal-policy", install_mode="none", weight="Very high", default_enabled=True)],
    )

    result = agentic_tool_license_matrix.evaluate_tools(agentic_tool_license_matrix.load_manifest(manifest), manifest)

    assert result.passed is True


def test_main_writes_markdown_and_json_reports(tmp_path: Path) -> None:
    manifest = tmp_path / "tools.json"
    markdown = tmp_path / "report.md"
    json_out = tmp_path / "result.json"
    write_manifest(manifest, [tool_row(name="safe-tool", license_spdx="Apache-2.0")])

    exit_code = agentic_tool_license_matrix.main(
        ["--manifest", str(manifest), "--markdown-out", str(markdown), "--json-out", str(json_out)]
    )

    assert exit_code == 0
    report = markdown.read_text(encoding="utf-8")
    assert "Agentic Mastery Tool License Gate Report" in report
    assert "safe-tool" in report
    data = json.loads(json_out.read_text(encoding="utf-8"))
    assert data["passed"] is True

def test_snake_case_cli_entrypoint_runs(tmp_path: Path) -> None:
    manifest = tmp_path / "tools.json"
    markdown = tmp_path / "report.md"
    write_manifest(manifest, [tool_row(name="safe-tool")])

    assert agentic_tool_license_matrix.main(["--manifest", str(manifest), "--markdown-out", str(markdown)]) == 0
    assert "safe-tool" in markdown.read_text(encoding="utf-8")
