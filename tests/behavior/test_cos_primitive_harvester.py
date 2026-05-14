from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "cos_primitive_harvester.py"


def run_harvester(text: str, repo: Path = REPO_ROOT) -> dict:
    result = subprocess.run(
        ["python3", str(SCRIPT), "--repo", str(repo), "--text", text, "--json"],
        text=True,
        capture_output=True,
        check=True,
        timeout=30,
    )
    return json.loads(result.stdout)


def test_create_primitive_for_repeatable_risky_verifiable_recipe() -> None:
    payload = run_harvester(
        "Esto no debería quedar como receta manual. Construyamos una primitiva automática "
        "para rotar y borrar snapshots de benchmark externos, hacer backup, ejecutar "
        "python3 scripts/cos_benchmark_snapshot_rotate.py --dry-run y validar con tests automatizados."
    )

    assert payload["decision"] == "CREATE_PRIMITIVE"
    assert payload["candidate_name"]
    assert "data-loss" in payload["risks"]
    assert any(path.startswith("scripts/cos_") for path in payload["artifact_plan"])
    assert payload["validation_plan"]


def test_improve_existing_when_matching_skill_exists_and_user_asks_edge_cases() -> None:
    payload = run_harvester(
        "Agrega más edge cases al cleanup preserved WIP: stashes con nombres raros, "
        "validation capsule dirty, tests automatizados y portabilidad."
    )

    assert payload["decision"] == "IMPROVE_EXISTING"
    assert payload["existing_match"]["name"] == "preserved-wip-cleanup"
    assert any("preserved-wip-cleanup" in path for path in payload["artifact_plan"])


def test_use_existing_when_request_matches_existing_primitive_without_change() -> None:
    payload = run_harvester(
        "Necesito limpiar stashes preservados y un validation capsule worktree usando el flujo existente."
    )

    assert payload["decision"] == "USE_EXISTING"
    assert payload["existing_match"]["name"] == "preserved-wip-cleanup"
    assert payload["artifact_plan"] == [payload["existing_match"]["path"]]


def test_use_existing_even_when_user_says_create_but_primitive_exists() -> None:
    payload = run_harvester(
        "Creá una skill automática para cleanup de stashes preservados y validation capsule worktrees."
    )

    assert payload["decision"] == "USE_EXISTING"
    assert payload["existing_match"]["name"] == "preserved-wip-cleanup"


def test_document_only_for_architecture_decision_without_action_layer() -> None:
    payload = run_harvester(
        "Documentemos un ADR sobre la decisión de llamar agentic primitives a esta capa, "
        "con alternativas y consecuencias."
    )

    assert payload["decision"] == "DOCUMENT_ONLY"
    assert payload["primitive_type"] == "documentation-decision"
    assert any(path.startswith("docs/02-Decisions/adrs/") for path in payload["artifact_plan"])


def test_discard_small_non_repeatable_chat() -> None:
    payload = run_harvester("gracias, después vemos")

    assert payload["decision"] == "DISCARD"
    assert payload["artifact_plan"] == []
    assert payload["validation_plan"] == []


def test_discard_ambiguous_preference_without_verifiable_workflow() -> None:
    payload = run_harvester("me gusta más que los nombres sean cortos")

    assert payload["decision"] == "DISCARD"


def test_create_when_it_can_improve_skills_and_other_primitives() -> None:
    payload = run_harvester(
        "Se puede crear una primitiva automática que revise conversaciones, clasifique si "
        "debe mejorar skills existentes, hooks u otras primitivas, descarte duplicados y "
        "genere tests automatizados? implementémoslo."
    )

    assert payload["decision"] in {"CREATE_PRIMITIVE", "IMPROVE_EXISTING"}
    assert payload["candidate_name"] == "primitive-harvester"
    assert payload["artifact_plan"]


def test_cli_accepts_conversation_file(tmp_path: Path) -> None:
    convo = tmp_path / "conversation.txt"
    convo.write_text(
        "Esto debería ser automático: script reusable con checklist, backup, tests y validación.",
        encoding="utf-8",
    )
    result = subprocess.run(
        ["python3", str(SCRIPT), "--repo", str(REPO_ROOT), "--conversation-file", str(convo), "--json"],
        text=True,
        capture_output=True,
        check=True,
        timeout=30,
    )
    payload = json.loads(result.stdout)
    assert payload["decision"] == "CREATE_PRIMITIVE"


def test_no_duplicate_when_existing_worktree_triage_matches() -> None:
    payload = run_harvester("Triagear worktree bb5a y port only unapplied work usando lo existente")

    assert payload["decision"] == "USE_EXISTING"
    assert payload["existing_match"]["name"] == "worktree-triage"


def test_artifact_plan_uses_canonical_portability_proof_path() -> None:
    payload = run_harvester(
        "Creemos un hook de gate para bloquear commits riesgosos con tests automatizados y portabilidad."
    )

    assert payload["decision"] == "CREATE_PRIMITIVE"
    assert any(path.startswith("hooks/") for path in payload["artifact_plan"])
    assert any(path.startswith("tests/red_team/portability/test_") and not path.endswith("_portability.py") for path in payload["artifact_plan"])
    assert any("cos-portability-proof-scaffold" not in command and "tests/red_team/portability/test_" in command for command in payload["validation_plan"])
