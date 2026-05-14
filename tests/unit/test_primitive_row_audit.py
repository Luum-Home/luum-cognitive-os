from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "primitive_row_audit.py"
spec = importlib.util.spec_from_file_location("primitive_row_audit", MODULE_PATH)
assert spec and spec.loader
primitive_row_audit = importlib.util.module_from_spec(spec)
sys.modules["primitive_row_audit"] = primitive_row_audit
spec.loader.exec_module(primitive_row_audit)


def make_repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / ".claude").mkdir(parents=True)
    (root / "manifests").mkdir()
    (root / "scripts").mkdir()
    (root / "hooks").mkdir()
    (root / "tests").mkdir()
    (root / "skills" / "demo").mkdir(parents=True)
    (root / "rules").mkdir()
    (root / ".cognitive-os" / "metrics").mkdir(parents=True)
    (root / ".claude" / "settings.json").write_text(
        json.dumps(
            {
                "hooks": {
                    "PreToolUse": [
                        {"hooks": [{"type": "command", "command": "bash hooks/proven.sh"}]}
                    ]
                }
            }
        )
    )
    (root / "hooks" / "proven.sh").write_text("#!/usr/bin/env bash\necho '{}' >> .cognitive-os/metrics/proven.jsonl\n")
    (root / "hooks" / "orphan.sh").write_text("#!/usr/bin/env bash\ntrue\n")
    (root / "hooks" / "demoted.sh").write_text("#!/usr/bin/env bash\ntrue\n")
    (root / "hooks" / "projected.sh").write_text("#!/usr/bin/env bash\ntrue\n")
    (root / "scripts" / "apply-efficiency-profile.sh").write_text('echo "projected.sh"\n')
    (root / "packages" / "demo" / "hooks").mkdir(parents=True)
    (root / "packages" / "demo" / "hooks" / "optional.sh").write_text("#!/usr/bin/env bash\ntrue\n")
    (root / "hooks" / "optional.sh").symlink_to(root / "packages" / "demo" / "hooks" / "optional.sh")
    (root / "tests" / "test_hooks.py").write_text("def test_proven(): assert 'proven.sh'\n")
    (root / "skills" / "demo" / "SKILL.md").write_text(
        "---\nname: demo\ntriggers: [demo]\n---\n# Demo\n\nContextual Trigger: demo\n"
    )
    (root / "rules" / "RULES-COMPACT.md").write_text("proven-rule.md\n")
    (root / "rules" / "proven-rule.md").write_text("<!-- TIER: 1 -->\n# Proven\n\nContextual Trigger: proven\n")
    (root / ".cognitive-os" / "metrics" / "proven.jsonl").write_text('{"ok": true}\n')
    (root / "manifests" / "reduction-demotions.json").write_text(
        json.dumps({"demotions": [{"family": "hooks", "path": "hooks/demoted.sh"}]})
    )
    return root


def test_row_audit_classifies_registered_tested_hook(tmp_path: Path) -> None:
    root = make_repo(tmp_path)

    rows = primitive_row_audit.audit(root)
    hook = next(row for row in rows if row.name == "proven.sh")
    orphan = next(row for row in rows if row.name == "orphan.sh")
    optional = next(row for row in rows if row.path == "hooks/optional.sh")
    projected = next(row for row in rows if row.name == "projected.sh")
    demoted = next(row for row in rows if row.name == "demoted.sh")

    assert hook.family == "hooks"
    assert hook.status == "proven"
    assert "events=PreToolUse" in hook.evidence
    assert orphan.status == "aspirational"
    assert orphan.severity == "medium"
    assert optional.status == "partial"
    assert optional.severity == "medium"
    assert projected.status == "partial"
    assert "projected" in projected.evidence
    assert demoted.status == "partial"
    assert demoted.severity == "low"


def test_row_audit_cli_writes_json_and_markdown(tmp_path: Path) -> None:
    root = make_repo(tmp_path)

    result = subprocess.run(
        [sys.executable, str(MODULE_PATH), "--project-dir", str(root)],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads((root / "docs" / "06-Daily" / "reports" / "primitive-row-audit-latest.json").read_text())
    assert payload["summary"]["hooks"]["total"] == 6
    assert "High-Severity Rows" in (root / "docs" / "06-Daily" / "reports" / "primitive-row-audit-latest.md").read_text()
