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
    bad = tmp_path / "cos_lib" / "bad.py"
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


ANCHORED_EVIDENCE = """\
version: 1
evidence:
- primitive: scripts/first
  harnesses:
  - shell-ci
  tests: &shared_tests
  - tests/unit/test_shared.py
  - tests/red_team/portability/test_shared_primitives.py
  rationale: Defines the anchor.
- primitive: templates/second.example.yaml
  harnesses:
  - shell-ci
  tests: *shared_tests
  rationale: Reuses the anchor.
patterns: []
"""


def test_fallback_parser_resolves_yaml_anchors_like_pyyaml() -> None:
    """Without PyYAML the audit must read the same evidence PyYAML reads."""
    import yaml

    mod = _load_module()
    fallback = mod._parse_behavior_evidence_fallback(ANCHORED_EVIDENCE)
    expected = yaml.safe_load(ANCHORED_EVIDENCE)

    shared = ["tests/unit/test_shared.py", "tests/red_team/portability/test_shared_primitives.py"]
    assert [row["tests"] for row in fallback["evidence"]] == [shared, shared]
    assert [row["tests"] for row in fallback["evidence"]] == [row["tests"] for row in expected["evidence"]]
    assert fallback["evidence"][1]["rationale"] == "Reuses the anchor."


def test_aliased_evidence_pairs_the_proof_without_pyyaml(tmp_path: Path, monkeypatch) -> None:
    """A primitive whose proof comes through a YAML alias stays paired when PyYAML is absent."""
    mod = _load_module()
    (tmp_path / "manifests").mkdir()
    (tmp_path / "manifests" / "primitive-behavior-evidence.yaml").write_text(ANCHORED_EVIDENCE, encoding="utf-8")
    proof = tmp_path / "tests" / "red_team" / "portability" / "test_shared_primitives.py"
    proof.parent.mkdir(parents=True)
    proof.write_text("def test_probe():\n    assert True\n", encoding="utf-8")

    paired = {}
    for label, yaml_module in (("with_pyyaml", mod.yaml), ("without_pyyaml", None)):
        monkeypatch.setattr(mod, "yaml", yaml_module)
        evidence = mod._load_behavior_evidence(tmp_path)
        paired[label] = mod._paired_portability_test(tmp_path, "templates/second.example.yaml", evidence)

    assert paired["with_pyyaml"] == "tests/red_team/portability/test_shared_primitives.py"
    assert paired["without_pyyaml"] == paired["with_pyyaml"]


def test_fallback_parser_agrees_with_pyyaml_on_the_real_manifest() -> None:
    """Every primitive's test list in the shipped manifest reads the same either way."""
    import yaml

    mod = _load_module()
    text = (REPO / "manifests" / "primitive-behavior-evidence.yaml").read_text(encoding="utf-8")
    with_pyyaml = {row["primitive"]: row.get("tests") for row in yaml.safe_load(text)["evidence"]}
    fallback = {row["primitive"]: row.get("tests") for row in mod._parse_behavior_evidence_fallback(text)["evidence"]}

    assert fallback == with_pyyaml
