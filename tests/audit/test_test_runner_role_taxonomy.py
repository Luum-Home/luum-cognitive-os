from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ROLE_DOC = ROOT / "docs" / "09-Quality" / "testing" / "test-runner-roles.md"
LEGACY_SCRIPTS = [
    ROOT / "scripts" / "pytest-with-summary.sh",
    ROOT / "scripts" / "cos-smoke.sh",
    ROOT / "scripts" / "test-cognitive-os.sh",
    ROOT / "scripts" / "test-cognitive-os-full.sh",
    ROOT / "scripts" / "test-all.sh",
    ROOT / "scripts" / "run-all-tests.sh",
]


def _role_table_rows(markdown: str) -> dict[str, list[str]]:
    rows: dict[str, str] = {}
    for line in markdown.splitlines():
        if not line.startswith("| "):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 2 or cells[0] in {"Role", "---"}:
            continue
        rows[cells[0]] = cells[1:]
    return rows


def _script_headers(script: Path) -> dict[str, str]:
    headers: dict[str, str] = {}
    for line in script.read_text(encoding="utf-8").splitlines()[:8]:
        if line.startswith("# ROLE:"):
            headers["ROLE"] = line.split(":", 1)[1].strip()
        if line.startswith("# CANONICAL:"):
            headers["CANONICAL"] = line.split(":", 1)[1].strip()
    return headers


def test_test_runner_role_taxonomy_maps_concerns_to_distinct_owners() -> None:
    """The test stack must separate selection, execution, reporting, governance, and lifecycle."""
    text = ROLE_DOC.read_text(encoding="utf-8")
    rows = _role_table_rows(text)

    assert {role: cells[1] for role, cells in rows.items() if role in {"Selection", "Execution", "Reporting", "Governance", "Lifecycle"}} == {
        "Selection": "`.cognitive-os/test-lanes.yaml`, `tests/conftest.py`, `cos-test focused / cluster / broad`",
        "Execution": "`cmd/cos-test`",
        "Reporting": "`scripts/pytest-with-summary.sh`, `tests/coverage-report.sh`, `scripts/cos_test_quality_audit.py`",
        "Governance": "hooks/skills such as `auto-verify`, `dod-gate`, `pre-commit-gate`, `coverage-enforcement`, `test-quality-audit`",
        "Lifecycle": "metrics JSONL, baselines, repair ledgers",
    }


def test_legacy_test_scripts_declare_role_and_canonical_entry() -> None:
    """Legacy scripts must not present themselves as competing generic runners."""
    for script in LEGACY_SCRIPTS:
        headers = _script_headers(script)
        assert set(headers) == {"ROLE", "CANONICAL"}, f"{script} headers = {headers}"
        assert headers["ROLE"] != headers["CANONICAL"], f"{script} role must not duplicate canonical command"


def test_run_tests_skill_points_to_role_taxonomy() -> None:
    skill = ROOT / "skills" / "run-tests" / "SKILL.md"
    text = skill.read_text(encoding="utf-8")
    rows = _role_table_rows(text)
    assert {role: cells[0] for role, cells in rows.items() if role in {"Selection + execution", "Persistent reporting fallback", "Opt-in startup smoke", "Legacy compatibility only"}} == {
        "Selection + execution": "`cos-test focused / cluster / broad`",
        "Persistent reporting fallback": "`scripts/pytest-with-summary.sh -- <pytest args>`",
        "Opt-in startup smoke": "`scripts/cos-smoke.sh`",
        "Legacy compatibility only": "`scripts/test-cognitive-os*.sh`, `scripts/test-all.sh`, `scripts/run-all-tests.sh`",
    }


def test_deprecated_cos_test_surfaces_do_not_use_legacy_pytest_runner() -> None:
    """run/dashboard/watch must proxy to focused/cluster/broad, not old runner.RunConfig paths."""
    for rel in [
        "cmd/cos-test/internal/cli/run.go",
        "cmd/cos-test/internal/cli/dashboard.go",
        "cmd/cos-test/internal/cli/watch.go",
    ]:
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert "runner.NewPytestRunner" not in text, rel
        assert "runner.RunConfig" not in text, rel
