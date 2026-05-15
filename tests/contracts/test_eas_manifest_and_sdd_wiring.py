from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
CONSUMER = ROOT / "manifests/primitive-consumer-availability.yaml"
LIFECYCLE = ROOT / "manifests/primitive-lifecycle.yaml"

EAS_SHARED_PATHS = {
    "rules/eas-evidence-artifact.md",
    "templates/eas.md",
    "scripts/eas_validate.py",
    "skills/sdd-spec/SKILL.md",
    "skills/sdd-tasks/SKILL.md",
    "skills/sdd-apply/SKILL.md",
    "skills/sdd-verify/SKILL.md",
}


def _yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_eas_primitives_have_consumer_availability_rows() -> None:
    data = _yaml(CONSUMER)
    rows_data = data.get("items", data) if isinstance(data, dict) else data
    exact_rows = {row["path"]: row for row in rows_data if isinstance(row, dict) and "path" in row}
    for path in EAS_SHARED_PATHS:
        assert path in exact_rows
        assert exact_rows[path]["status"] == "shared-surface"


def test_eas_primitives_have_lifecycle_rows() -> None:
    data = _yaml(LIFECYCLE)
    rows_data = data.get("primitives", data) if isinstance(data, dict) else data
    rows = {row["id"]: row for row in rows_data if isinstance(row, dict) and "id" in row}
    for path in EAS_SHARED_PATHS:
        assert path in rows
        assert rows[path]["owner_adr"] == "ADR-317"
        assert rows[path]["consumer_accessibility"] == "lifecycle-declared-shared-surface"


def test_sdd_phase_skills_are_wired_to_eas_and_validator() -> None:
    expected = {
        "skills/sdd-spec/SKILL.md": ["templates/eas.md", "REQ-*", "AC-*", "Detractor"],
        "skills/sdd-tasks/SKILL.md": ["gap matrix", "AC-*", "OBJ-*", "scripts/eas_validate.py"],
        "skills/sdd-apply/SKILL.md": ["REQ-*", "AC-*", "OBJ-*", "EAS"],
        "skills/sdd-verify/SKILL.md": ["scripts/eas_validate.py", "adversarial-review", "residual risks"],
    }
    for relpath, needles in expected.items():
        text = (ROOT / relpath).read_text(encoding="utf-8")
        assert "<!-- SCOPE: both -->" in text
        for needle in needles:
            assert needle in text
