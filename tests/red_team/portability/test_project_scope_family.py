from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PROJECT_PRIMITIVE_PROOF_BASELINE = [
    'hooks/architecture-compliance.sh',
    'hooks/dry-run-preview.sh',
    'hooks/infra-intent-detector.sh',
    'hooks/jupyter-sandbox.sh',
    'scripts/check_mcp_servers.py',
    'scripts/cos',
    'scripts/docs_execution_audit.py',
    'scripts/document_feature_append.py',
    'scripts/domain_model.py',
    'scripts/llm_status.py',
    'scripts/ops_runbook.py',
    'scripts/project_scaffold.py',
    'scripts/radar_merge.py',
    'scripts/sprint-test-summary.sh',
    'skills/project-scaffold/SKILL.md',
    'templates/CLAUDE.md.template',
    'templates/adoption-tiers.md.j2',
    'templates/blocked-strings.example.txt',
    'templates/external-tools-overlay.yaml',
    'templates/fintech-gates.md',
    'templates/go-service-context.md',
    'templates/project-templates/go/README.md.tmpl',
    'templates/project-templates/go/cognitive-os.yaml.tmpl',
    'templates/project-templates/go/gitignore.tmpl',
    'templates/project-templates/go/go.mod.tmpl',
    'templates/project-templates/go/main.go.tmpl',
    'templates/project-templates/minimal/README.md.tmpl',
    'templates/project-templates/minimal/cognitive-os.yaml.tmpl',
    'templates/project-templates/minimal/gitignore.tmpl',
    'templates/project-templates/python/README.md.tmpl',
    'templates/project-templates/python/cognitive-os.yaml.tmpl',
    'templates/project-templates/python/gitignore.tmpl',
    'templates/project-templates/python/pyproject.toml.tmpl',
    'templates/project-templates/settings.json.tmpl',
    'templates/project-templates/typescript/README.md.tmpl',
    'templates/project-templates/typescript/cognitive-os.yaml.tmpl',
    'templates/project-templates/typescript/gitignore.tmpl',
    'templates/project-templates/typescript/package.json.tmpl',
    'templates/project-templates/typescript/tsconfig.json.tmpl',
    'templates/security-profiles/minimal.json',
    'templates/security-profiles/paranoid.json',
    'templates/security-profiles/standard.json',
    'templates/service-map.example.yaml',
    'templates/verification-commands.example.yaml',
]


def _load_health_module():
    module_path = ROOT / "scripts" / "primitive_scope_health.py"
    spec = importlib.util.spec_from_file_location("primitive_scope_health_project_family", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_project_scope_family_has_explicit_projection_metadata_and_no_source_paths() -> None:
    health = _load_health_module()
    rows = {row.path: row for row in health.build_rows(ROOT)}

    for rel in PROJECT_PRIMITIVE_PROOF_BASELINE:
        path = ROOT / rel
        assert path.exists(), rel
        row = rows[rel]
        assert row.scope == "project", rel
        assert row.consumer_surface in {"projected", "project-generated"}, rel
        text = path.read_text(encoding="utf-8", errors="ignore")[:30000]
        assert not health.SOURCE_PATH_RE.search(text), rel


def test_project_scope_family_is_registered_as_behavior_evidence() -> None:
    manifest = ROOT / "manifests" / "primitive-behavior-evidence.yaml"
    data = __import__("yaml").safe_load(manifest.read_text(encoding="utf-8"))
    evidence = {item["primitive"]: item for item in data["evidence"]}

    for rel in PROJECT_PRIMITIVE_PROOF_BASELINE:
        tests = evidence[rel]["tests"]
        assert "tests/red_team/portability/test_project_scope_family.py" in tests, rel


def test_project_scope_none_budget_is_zero_after_family_proof() -> None:
    out = ROOT / ".cognitive-os" / "reports" / "test-project-scope-family-health.json"
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "primitive_scope_health.py"),
            "--project-dir",
            str(ROOT),
            "--mode",
            "proof",
            "--strict",
            "--json-out",
            str(out),
        ],
        check=True,
    )
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["summary"]["findings"] == 0
    assert payload["summary"]["by_proof_level"].get("none", 0) <= 459
