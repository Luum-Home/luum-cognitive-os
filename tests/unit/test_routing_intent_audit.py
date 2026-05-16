from pathlib import Path

from scripts import routing_intent_audit as ria


def _write_skill(root: Path, name: str, frontmatter: str) -> Path:
    skill_dir = root / "skills" / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    path = skill_dir / "SKILL.md"
    path.write_text(frontmatter, encoding="utf-8")
    return path


def test_audit_reports_missing_routing_intents(tmp_path: Path) -> None:
    _write_skill(tmp_path, "missing", "---\nname: missing\ndescription: Missing intents\n---\n")
    report = ria.audit(tmp_path)
    assert report.skill_count == 1
    assert report.issue_count == 1
    assert report.audits[0].issues[0].code == "missing-routing-intents"


def test_audit_accepts_specific_routing_intent(tmp_path: Path) -> None:
    _write_skill(
        tmp_path,
        "review",
        "---\n"
        "name: review\n"
        "routing_intents:\n"
        "- intent: review_changed_code\n"
        "  description: User asks to review changed source files for bugs and missing tests.\n"
        "---\n",
    )
    report = ria.audit(tmp_path)
    assert report.skill_count == 1
    assert report.issue_count == 0
    assert report.skills_with_intents == 1


def test_audit_flags_generic_routing_intent(tmp_path: Path) -> None:
    _write_skill(
        tmp_path,
        "generic",
        "---\nname: generic\nrouting_intents:\n- description: Use this skill.\n---\n",
    )
    report = ria.audit(tmp_path)
    codes = [issue.code for issue in report.audits[0].issues]
    assert "low-signal-routing-intent" in codes
