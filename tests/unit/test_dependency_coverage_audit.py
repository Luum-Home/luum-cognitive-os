from __future__ import annotations

import json
import subprocess
from pathlib import Path

import yaml

from lib.dependency_coverage_audit import build_report, collect_command_probes


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def manifest_payload() -> dict:
    return {
        "schema_version": 1,
        "python": {
            "required": ["pyyaml>=6.0"],
            "groups": {"testing": ["pytest>=8.0"]},
        },
        "tools": [
            {
                "name": "jq",
                "criticality": "required",
                "check": "jq --version",
                "install": {"any": "brew install jq"},
            },
            {
                "name": "unused-tool",
                "criticality": "optional",
                "check": "unused-tool --version",
                "install": {"any": "brew install unused-tool"},
            },
        ],
        "mcp_servers": [],
        "profiles": {
            "default": {
                "python_groups": [],
                "tools_required": ["jq"],
                "tools_recommended": [],
                "mcp_servers_recommended": [],
            },
            "full": {
                "python_groups": ["testing"],
                "tools_required": ["jq"],
                "tools_recommended": ["unused-tool"],
                "mcp_servers_recommended": [],
            },
        },
    }


def write_manifest(root: Path) -> Path:
    path = root / "manifests" / "dependencies.yaml"
    write(path, yaml.safe_dump(manifest_payload(), sort_keys=False))
    return path


def names(bucket: list[dict]) -> set[str]:
    return {row["name"] for row in bucket}


def test_build_report_classifies_missing_tools_python_lanes_and_false_positives(tmp_path: Path) -> None:
    manifest = write_manifest(tmp_path)
    write(
        tmp_path / "scripts" / "probe.sh",
        """#!/usr/bin/env bash
safe_jsonl_append() { :; }
command -v jq >/dev/null
command -v shellcheck >/dev/null
command -v safe_jsonl_append >/dev/null
command -v cat >/dev/null
""",
    )
    write(
        tmp_path / "pyproject.toml",
        '[project]\nname = "demo"\ndependencies = ["rich>=14", "pyyaml>=6"]\n',
    )
    write(tmp_path / "requirements" / "dependency-lanes" / "semantic.txt", "numpy>=1.26\n")

    report = build_report(tmp_path, manifest_path=manifest)

    assert report["schema_version"] == "cos-deps-coverage-audit.v1"
    assert "shellcheck" in names(report["missing_from_manifest"])
    assert "rich" in names(report["missing_from_manifest"])
    assert "numpy" in names(report["optional_lane_needed"])
    assert "cat" in names(report["platform_builtin"])
    assert "safe_jsonl_append" in names(report["internal_helper_false_positive"])
    assert "unused-tool" in names(report["manifested_but_unused"])


def test_collect_command_probes_reads_shutil_subprocess_and_install_commands(tmp_path: Path) -> None:
    write(
        tmp_path / "scripts" / "probe.py",
        """import shutil, subprocess
shutil.which("redis-cli")
subprocess.run(["git", "status"], check=False)
""",
    )
    write(
        tmp_path / "scripts" / "install.sh",
        """#!/usr/bin/env bash
brew install vale
cargo install depyler
go install github.com/acme/tooler@latest
npm install -g promptfoo
python3 -m pip install --user py2many
""",
    )

    rows = collect_command_probes(tmp_path)
    found = {(row.name, row.sources[0].source) for row in rows}

    assert ("redis-cli", "shutil-which") in found
    assert ("git", "subprocess") in found
    assert ("vale", "brew-install") in found
    assert ("depyler", "cargo-install") in found
    assert ("tooler", "go-install") in found
    assert ("promptfoo", "npm-install-global") in found
    assert ("py2many", "pip-install") in found


def test_cli_emits_json(tmp_path: Path) -> None:
    manifest = write_manifest(tmp_path)
    write(tmp_path / "scripts" / "probe.sh", "command -v shellcheck >/dev/null\n")

    result = subprocess.run(
        [
            "python3",
            str(Path(__file__).resolve().parents[2] / "lib" / "dependency_coverage_audit.py"),
            "--root",
            str(tmp_path),
            "--manifest",
            str(manifest),
            "--json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    payload = json.loads(result.stdout)
    assert payload["summary"]["missing_from_manifest"] == 1
    assert payload["missing_from_manifest"][0]["name"] == "shellcheck"
