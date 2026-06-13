from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SKILL_PATHS = [
    ROOT / "skills" / "so-impact-eval" / "SKILL.md",
    ROOT / ".cognitive-os" / "skills" / "so-impact-eval" / "SKILL.md",
    ROOT / ".cognitive-os" / "skills" / "cos" / "so-impact-eval" / "SKILL.md",
    ROOT / ".claude" / "skills" / "so-impact-eval" / "SKILL.md",
]


def frontmatter(path: Path) -> dict:
    body = path.read_text(encoding="utf-8")
    assert body.startswith("---\n")
    raw = body.split("---", 2)[1]
    return yaml.safe_load(raw)


def test_so_impact_eval_skill_projected_to_all_surfaces() -> None:
    canonical = SKILL_PATHS[0].read_text(encoding="utf-8")
    for path in SKILL_PATHS:
        assert path.exists(), str(path)
        assert path.read_text(encoding="utf-8") == canonical


def test_so_impact_eval_skill_has_conversational_triggers() -> None:
    fm = frontmatter(SKILL_PATHS[0])
    triggers = set(fm["triggers"])
    assert "/so-impact-eval" in triggers
    assert "/so-impact-smoke" in triggers
    assert "run SO-wide impact eval" in triggers
    assert "compará vanilla vs full SO" in triggers
    assert "compare vanilla vs full SO" in triggers
    assert "cos-so-impact-eval" in fm["description"]


def test_so_impact_eval_skill_documents_short_commands() -> None:
    body = SKILL_PATHS[0].read_text(encoding="utf-8")
    assert "make test-so-impact-smoke" in body
    assert "--run-id chat-smoke" in body
    assert "/tmp/cos-so-impact-eval/money-format-refactor/chat-smoke/report.md" in body


def test_makefile_exposes_so_impact_smoke_target() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    assert "test-so-impact-smoke:" in makefile
    assert "scripts/cos-so-impact-eval run" in makefile
    assert "No-cost SO-wide impact smoke" in makefile
