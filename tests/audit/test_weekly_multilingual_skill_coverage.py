from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.audit

REPO_ROOT = Path(__file__).resolve().parents[2]

WEEKLY_CONVERSATIONAL_SKILLS = {
    "agent-run-supervision": {
        "es": ("como venimos", "status del agente", "murió el agente", "está trabado"),
        "pt": ("como estamos", "agente travado"),
    },
    "artifact-workflow": {
        "es": ("flujo de artefactos", "grafo de trabajo", "segunda revisión"),
        "pt": ("fluxo de artefatos", "grafo de trabalho"),
    },
    "branch-worktree-closure": {
        "es": ("mergea todas las branches", "revisa los stashes", "cerrar ramas"),
        "pt": ("levar branches", "revisar stashes"),
    },
    "epistemic-review": {
        "es": ("audita honestamente", "verifica claim", "testigo interesado"),
        "pt": ("auditoria cética", "verificar afirmação"),
    },
    "graphify-query": {
        "es": ("grafo de conocimiento", "grafo del repo", "consulta graphify"),
        "pt": ("grafo do repositorio", "consulta de grafo"),
    },
    "lean-code": {
        "es": ("código liviano", "menos código", "sin dependencias innecesarias"),
        "pt": ("código enxuto", "sem dependências desnecessárias"),
    },
    "skill-creator": {
        "es": ("crear skill", "habilidad de agente"),
        "pt": ("criar skill", "criar habilidade"),
    },
    "skill-optimization": {
        "es": ("optimizar skill", "mejorar skill"),
        "pt": ("otimizar skill", "melhorar skill"),
    },
    "so-impact-eval": {
        "es": ("evaluar impacto del SO", "comparar vanilla vs SO completo"),
        "pt": ("avaliar impacto do SO",),
    },
}

PROJECTION_ROOTS = (
    REPO_ROOT / "skills",
    REPO_ROOT / ".claude" / "skills",
    REPO_ROOT / ".codex" / "skills",
    REPO_ROOT / ".cognitive-os" / "skills",
    REPO_ROOT / ".cognitive-os" / "skills" / "cos",
)


@pytest.mark.parametrize("skill, expected", sorted(WEEKLY_CONVERSATIONAL_SKILLS.items()))
def test_weekly_conversational_skill_has_spanish_and_portuguese_aliases(skill: str, expected: dict[str, tuple[str, ...]]) -> None:
    source = REPO_ROOT / "skills" / skill / "SKILL.md"
    assert source.exists(), skill
    text = source.read_text(encoding="utf-8").lower()
    for language, aliases in expected.items():
        assert any(alias.lower() in text for alias in aliases), f"{skill} missing {language} aliases"


@pytest.mark.parametrize("skill", sorted(WEEKLY_CONVERSATIONAL_SKILLS))
def test_existing_skill_projections_preserve_multilingual_aliases(skill: str) -> None:
    source = REPO_ROOT / "skills" / skill / "SKILL.md"
    source_text = source.read_text(encoding="utf-8")
    checked = 0
    for root in PROJECTION_ROOTS[1:]:
        projected = root / skill / "SKILL.md"
        if not projected.exists():
            continue
        checked += 1
        assert projected.read_text(encoding="utf-8") == source_text
    assert checked >= 1, f"{skill} has no projected SKILL.md surface"
