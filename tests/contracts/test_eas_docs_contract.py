from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EAS_DOC = ROOT / "docs/05-Methodology/root/executable-acceptance-specification.md"
EAS_TEMPLATE = ROOT / "templates/eas.md"
EAS_RULE = ROOT / "rules/eas-evidence-artifact.md"
EAS_ADR = ROOT / "docs/02-Decisions/adrs/ADR-317-executable-acceptance-specification-eas.md"
EAS_VALIDATOR = ROOT / "scripts/eas_validate.py"


REQUIRED_SECTIONS = [
    "Intent",
    "Requirements",
    "Non-goals",
    "Executable Acceptance Criteria",
    "Gap Matrix",
    "Adversarial Personas",
    "Detractor Objection Log",
    "Verification Commands",
    "Residual Risks",
]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_eas_artifacts_exist() -> None:
    assert EAS_DOC.is_file()
    assert EAS_TEMPLATE.is_file()
    assert EAS_RULE.is_file()
    assert EAS_ADR.is_file()
    assert EAS_VALIDATOR.is_file()


def test_eas_doc_defines_required_sections() -> None:
    text = _read(EAS_DOC)
    for section in REQUIRED_SECTIONS:
        assert section in text


def test_eas_template_contains_required_sections() -> None:
    text = _read(EAS_TEMPLATE)
    for section in REQUIRED_SECTIONS:
        assert f"## {section}" in text


def test_eas_rule_points_to_template_validator_and_sdd_integration() -> None:
    text = _read(EAS_RULE)
    assert "templates/eas.md" in text
    assert "scripts/eas_validate.py" in text
    for phase in ["sdd-spec", "sdd-tasks", "sdd-apply", "sdd-verify", "sdd-archive"]:
        assert phase in text


def test_eas_validator_rejects_incomplete_artifact(tmp_path: Path) -> None:
    import subprocess

    incomplete = tmp_path / "incomplete-eas.md"
    incomplete.write_text("# EAS: incomplete\n\n## Intent\nOnly intent is present.\n", encoding="utf-8")

    result = subprocess.run(
        ["python3", "scripts/eas_validate.py", str(incomplete)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )

    assert result.returncode != 0
    assert "missing required section" in result.stdout.lower()
