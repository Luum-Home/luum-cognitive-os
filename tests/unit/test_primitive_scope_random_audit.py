from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "primitive_scope_random_audit.py"
spec = importlib.util.spec_from_file_location("primitive_scope_random_audit", MODULE_PATH)
assert spec and spec.loader
primitive_scope_random_audit = importlib.util.module_from_spec(spec)
sys.modules["primitive_scope_random_audit"] = primitive_scope_random_audit
spec.loader.exec_module(primitive_scope_random_audit)


ROWS = [
    {
        "path": "hooks/a.sh",
        "declared_scope": "both",
        "suggested_scope": "both",
        "effective_scope": "both",
        "confidence": "high",
        "decision_source": "consumer-availability+lifecycle",
        "paired_portability_test": "tests/red_team/portability/test_a.py",
        "contradiction": "",
        "evidence": [{"source": "consumer-availability", "detail": "shared-surface"}],
    },
    {
        "path": "hooks/b.sh",
        "declared_scope": "os-only",
        "suggested_scope": "os-only",
        "effective_scope": "os-only",
        "confidence": "medium",
        "decision_source": "consumer-availability",
        "paired_portability_test": None,
        "contradiction": "",
        "evidence": [{"source": "consumer-availability", "detail": "maintainer-only"}],
    },
    {
        "path": "skills/c/SKILL.md",
        "declared_scope": "project",
        "suggested_scope": "project",
        "effective_scope": "project",
        "confidence": "medium",
        "decision_source": "consumer-availability",
        "paired_portability_test": None,
        "contradiction": "",
        "evidence": [{"source": "consumer-availability", "detail": "projected-consumer-surface"}],
    },
    {
        "path": "rules/d.md",
        "declared_scope": "both",
        "suggested_scope": "both",
        "effective_scope": "both",
        "confidence": "medium",
        "decision_source": "semantic-pattern",
        "paired_portability_test": None,
        "contradiction": "",
        "evidence": [{"source": "semantic-pattern", "detail": "shared-rule"}],
    },
]


def test_select_sample_is_seeded_and_stratified_by_effective_scope() -> None:
    first = primitive_scope_random_audit.select_sample(ROWS, seed=7, per_scope=1, total=3, scopes=None, confidences=None)
    second = primitive_scope_random_audit.select_sample(ROWS, seed=7, per_scope=1, total=3, scopes=None, confidences=None)

    assert [row.path for row in first] == [row.path for row in second]
    assert {row.effective_scope for row in first} == {"both", "os-only", "project"}
    assert all(row.review_prompt for row in first)


def test_confidence_filter_limits_random_sample() -> None:
    sample = primitive_scope_random_audit.select_sample(ROWS, seed=1, per_scope=0, total=10, scopes=None, confidences={"medium"})

    assert {row.confidence for row in sample} == {"medium"}
    assert {row.path for row in sample} == {"hooks/b.sh", "skills/c/SKILL.md", "rules/d.md"}


def test_cli_writes_json_and_markdown_report(tmp_path: Path) -> None:
    json_out = tmp_path / "audit.json"
    md_out = tmp_path / "audit.md"

    result = subprocess.run(
        [
            sys.executable,
            str(MODULE_PATH),
            "--project-dir",
            str(Path(__file__).resolve().parents[2]),
            "--seed",
            "20260515",
            "--per-scope",
            "1",
            "--total",
            "3",
            "--json-out",
            str(json_out),
            "--md-out",
            str(md_out),
        ],
        text=True,
        capture_output=True,
        check=False,
        timeout=60,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    payload = json.loads(json_out.read_text())
    assert payload["schema_version"] == "primitive-scope-random-audit/v1"
    assert payload["sample_summary"]["total"] == 3
    assert "Manual review checklist" in md_out.read_text()
