from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import yaml

MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "primitive_scope_dependency_audit.py"
spec = importlib.util.spec_from_file_location("primitive_scope_dependency_audit", MODULE_PATH)
assert spec and spec.loader
primitive_scope_dependency_audit = importlib.util.module_from_spec(spec)
sys.modules["primitive_scope_dependency_audit"] = primitive_scope_dependency_audit
spec.loader.exec_module(primitive_scope_dependency_audit)


def test_project_hook_referencing_os_only_rule_is_reported(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    (root / "hooks").mkdir(parents=True)
    (root / "rules").mkdir()
    (root / "manifests").mkdir()
    (root / "hooks" / "consumer-hook.sh").write_text(
        "#!/usr/bin/env bash\n# SCOPE: project\necho 'See rules/internal-policy.md'\n"
    )
    (root / "rules" / "internal-policy.md").write_text("<!-- SCOPE: os-only -->\n# Internal policy\n")
    (root / "manifests" / "primitive-consumer-availability.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": "primitive-consumer-availability.v1",
                "items": [
                    {"path": "hooks/consumer-hook.sh", "status": "projected-consumer-surface", "rationale": "fixture"},
                    {"path": "rules/internal-policy.md", "status": "maintainer-only", "rationale": "fixture"},
                ],
            }
        )
    )

    findings = primitive_scope_dependency_audit.build_findings(root)

    assert len(findings) == 1
    assert findings[0].hook == "hooks/consumer-hook.sh"
    assert findings[0].rule == "rules/internal-policy.md"
