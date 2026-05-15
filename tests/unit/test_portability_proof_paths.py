from __future__ import annotations

from lib.portability_proof_paths import paired_candidates, suggested_test_path


def test_root_skill_uses_skill_specific_proof_path() -> None:
    rel = "skills/add-hook/SKILL.md"

    assert paired_candidates(rel)[0] == "tests/red_team/portability/test_skill_add_hook.py"
    assert suggested_test_path(rel) == "tests/red_team/portability/test_skill_add_hook.py"


def test_package_skill_uses_package_specific_and_aggregate_proof_paths() -> None:
    rel = "packages/quality-gates/skills/dod-check/SKILL.md"

    candidates = paired_candidates(rel)

    assert candidates[0] == "tests/red_team/portability/test_package_skill_quality_gates_dod_check.py"
    assert candidates[1] == "tests/red_team/portability/test_package_skills.py"
    assert suggested_test_path(rel) == "tests/red_team/portability/test_package_skill_quality_gates_dod_check.py"
