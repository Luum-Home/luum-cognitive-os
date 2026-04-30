from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "docs_duplicate_audit.py"
spec = importlib.util.spec_from_file_location("docs_duplicate_audit", MODULE_PATH)
assert spec and spec.loader
docs_duplicate_audit = importlib.util.module_from_spec(spec)
sys.modules["docs_duplicate_audit"] = docs_duplicate_audit
spec.loader.exec_module(docs_duplicate_audit)


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def long_doc(title: str, repeated: str) -> str:
    body = " ".join([repeated] * 140)
    return f"# {title}\n\n{body}\n"


def test_detects_new_duplicate_pairs_against_empty_baseline(tmp_path: Path) -> None:
    write(tmp_path / "docs/a.md", long_doc("Alpha", "portable agent governance memory verification"))
    write(tmp_path / "docs/b.md", long_doc("Alpha", "portable agent governance memory verification"))

    data = docs_duplicate_audit.audit(
        tmp_path,
        ["docs"],
        min_tokens=20,
        shingle_size=3,
        threshold=0.72,
        baseline_path=None,
    )

    assert data["duplicate_pairs"] == 1
    assert data["new_duplicate_pairs"] == 1
    assert "docs/a.md :: docs/b.md" in data["new_findings"]


def test_baseline_suppresses_existing_duplicate_pairs(tmp_path: Path) -> None:
    write(tmp_path / "docs/a.md", long_doc("Alpha", "portable agent governance memory verification"))
    write(tmp_path / "docs/b.md", long_doc("Alpha", "portable agent governance memory verification"))
    write(
        tmp_path / "docs/reports/baseline.json",
        '{"pair_keys":["docs/a.md :: docs/b.md"]}\n',
    )

    data = docs_duplicate_audit.audit(
        tmp_path,
        ["docs"],
        min_tokens=20,
        shingle_size=3,
        threshold=0.72,
        baseline_path=tmp_path / "docs/reports/baseline.json",
    )

    assert data["duplicate_pairs"] == 1
    assert data["new_duplicate_pairs"] == 0


def test_render_markdown_lists_new_findings() -> None:
    markdown = docs_duplicate_audit.render_markdown(
        {
            "timestamp": "2026-04-30T00:00:00+00:00",
            "docs_scanned": 2,
            "duplicate_pairs": 1,
            "new_duplicate_pairs": 1,
            "new_findings": ["docs/a.md :: docs/b.md"],
            "findings": [
                {
                    "similarity": 1.0,
                    "reason": "content_similarity",
                    "left": "docs/a.md",
                    "right": "docs/b.md",
                }
            ],
        }
    )

    assert "Documentation Duplicate Audit" in markdown
    assert "docs/a.md :: docs/b.md" in markdown
