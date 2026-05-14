from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "cos-scope-both-portability-audit"


def _load_module():
    loader = importlib.machinery.SourceFileLoader("scope_both_portability_audit", str(SCRIPT))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[loader.name] = module
    spec.loader.exec_module(module)
    return module


def test_inventory_detects_covered_and_missing_scope_both_artifacts(tmp_path: Path) -> None:
    mod = _load_module()
    hook = tmp_path / "hooks" / "sample-hook.sh"
    hook.parent.mkdir(parents=True)
    hook.write_text("#!/usr/bin/env bash\n# SCOPE: both\necho ok\n", encoding="utf-8")
    script = tmp_path / "scripts" / "missing-tool"
    script.parent.mkdir(parents=True)
    script.write_text("#!/usr/bin/env bash\n# SCOPE: both\necho missing\n", encoding="utf-8")
    proof = tmp_path / "tests" / "red_team" / "portability" / "test_sample-hook.py"
    proof.parent.mkdir(parents=True)
    proof.write_text("def test_falsification_probe():\n    assert True\n", encoding="utf-8")

    rows, summary = mod.build_inventory(tmp_path)
    by_artifact = {row.artifact: row for row in rows}

    assert summary["total"] == 2
    assert summary["covered"] == 1
    assert summary["missing"] == 1
    assert by_artifact["hooks/sample-hook.sh"].paired_test == "tests/red_team/portability/test_sample-hook.py"
    assert by_artifact["scripts/missing-tool"].suggested_test_path == "tests/red_team/portability/test_missing-tool.py"


def test_report_writer_emits_json_and_markdown(tmp_path: Path) -> None:
    mod = _load_module()
    hook = tmp_path / "hooks" / "x.sh"
    hook.parent.mkdir(parents=True)
    hook.write_text("#!/usr/bin/env bash\n# SCOPE: both\necho x\n", encoding="utf-8")
    rows, summary = mod.build_inventory(tmp_path)
    json_path = tmp_path / "out" / "audit.json"
    md_path = tmp_path / "out" / "audit.md"

    mod.write_reports(tmp_path, rows, summary, json_path, md_path)

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "scope-both-portability-audit/v1"
    assert payload["summary"]["missing"] == 1
    assert "Missing proofs" in md_path.read_text(encoding="utf-8")


def test_inventory_suggests_skill_specific_proof_path(tmp_path: Path) -> None:
    mod = _load_module()
    skill = tmp_path / "skills" / "add-hook" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("<!-- SCOPE: both -->\n---\nname: add-hook\n---\n", encoding="utf-8")

    rows, summary = mod.build_inventory(tmp_path)

    assert summary["missing"] == 1
    assert rows[0].artifact == "skills/add-hook/SKILL.md"
    assert rows[0].suggested_test_path == "tests/red_team/portability/test_skill_add_hook.py"


def test_cli_no_write_does_not_create_reports(tmp_path: Path) -> None:
    hook = tmp_path / "hooks" / "x.sh"
    hook.parent.mkdir(parents=True)
    hook.write_text("#!/usr/bin/env bash\n# SCOPE: both\necho x\n", encoding="utf-8")

    import subprocess

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--repo-root",
            str(tmp_path),
            "--json",
            "--no-write",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["summary"]["missing"] == 1
    assert not (tmp_path / ".cognitive-os" / "reports" / "scope-both-portability-audit.json").exists()
