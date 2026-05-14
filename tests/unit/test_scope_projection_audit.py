from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "cos-scope-projection-audit"


def _load_module():
    loader = importlib.machinery.SourceFileLoader("scope_projection_audit", str(SCRIPT))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[loader.name] = module
    spec.loader.exec_module(module)
    return module


def test_report_blocks_invalid_scope_and_missing_both_proof(tmp_path: Path) -> None:
    mod = _load_module()
    hook = tmp_path / "hooks" / "portable.sh"
    hook.parent.mkdir(parents=True)
    hook.write_text("#!/usr/bin/env bash\n# SCOPE: both\necho ok\n", encoding="utf-8")
    bad = tmp_path / "lib" / "bad.py"
    bad.parent.mkdir(parents=True)
    bad.write_text("# SCOPE: OS\n", encoding="utf-8")

    report = mod.build_report(tmp_path)
    codes = {finding["code"] for finding in report["findings"]}

    assert report["schema_version"] == "scope-projection-audit/v1"
    assert "invalid-scope-marker" in codes
    assert "both-without-portability-proof" in codes
    assert report["summary"]["block_findings"] == 2


def test_report_accepts_both_proof_and_blocks_os_only_projection(tmp_path: Path) -> None:
    mod = _load_module()
    hook = tmp_path / "hooks" / "portable.sh"
    hook.parent.mkdir(parents=True)
    hook.write_text("#!/usr/bin/env bash\n# SCOPE: both\necho ok\n", encoding="utf-8")
    proof = tmp_path / "tests" / "red_team" / "portability" / "test_portable.py"
    proof.parent.mkdir(parents=True)
    proof.write_text("def test_falsification_probe():\n    assert True\n", encoding="utf-8")
    projected = tmp_path / "consumer" / ".cognitive-os" / "hooks" / "cos" / "internal.sh"
    projected.parent.mkdir(parents=True)
    projected.write_text("#!/usr/bin/env bash\n# SCOPE: os-only\n", encoding="utf-8")

    report = mod.build_report(tmp_path, projection_root=tmp_path / "consumer")

    assert report["summary"]["both_total"] == 1
    assert report["summary"]["both_with_proofs"] == 1
    assert {finding["code"] for finding in report["findings"]} == {"os-only-projected-to-project"}


def test_writer_outputs_json_and_markdown(tmp_path: Path) -> None:
    mod = _load_module()
    hook = tmp_path / "hooks" / "os.sh"
    hook.parent.mkdir(parents=True)
    hook.write_text("#!/usr/bin/env bash\n# SCOPE: os-only\necho ok\n", encoding="utf-8")
    report = mod.build_report(tmp_path)
    md = mod.render_markdown(report)

    assert "Scope Projection Audit" in md
    assert "No findings" in md
    assert json.loads(json.dumps(report))["summary"]["source_total"] == 1
