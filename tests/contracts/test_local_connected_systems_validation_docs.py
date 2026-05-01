from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOC = PROJECT_ROOT / "docs" / "manual-tests" / "local-connected-systems-validation.md"


def _section(markdown: str, heading: str) -> str:
    lines = markdown.splitlines()
    start = lines.index(heading)
    body: list[str] = []
    for line in lines[start + 1 :]:
        if line.startswith("## "):
            break
        body.append(line)
    return "\n".join(body)


def _table_rows(section: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in section.splitlines():
        if not line.startswith("|") or "---" in line:
            continue
        rows.append([cell.strip() for cell in line.strip("|").split("|")])
    return rows


def _commands(section: str) -> list[str]:
    commands: list[str] = []
    in_block = False
    for line in section.splitlines():
        if line.strip() == "```bash":
            in_block = True
            continue
        if in_block and line.strip() == "```":
            in_block = False
            continue
        if in_block and line.strip() and not line.strip().endswith("\\"):
            commands.append(line.strip())
    return commands


def test_local_connected_systems_validation_uses_manifest_as_source_of_truth() -> None:
    text = DOC.read_text(encoding="utf-8")
    section = _section(text, "## Source of Truth")
    rows = _table_rows(section)
    contracts = {row[0] for row in rows[1:]}

    assert {
        "`manifests/dependencies.yaml`",
        "`scripts/manifest-check.sh`",
        "`scripts/setup.sh`",
        "`scripts/cos-doctor-tools.sh`",
        "`scripts/cos-bootstrap.sh`",
    }.issubset(contracts)
    assert text.index("## Source of Truth") < text.index("## Profiles")


def test_local_connected_systems_validation_bounds_automatic_installation_by_behavior() -> None:
    text = DOC.read_text(encoding="utf-8")
    section = _section(text, "## Automatic Install Boundary")

    assert "`scripts/setup.sh` may install" in section
    assert "`scripts/manifest-check.sh` is a verifier, not an installer" in section
    assert "`scripts/cos-doctor-tools.sh` is advisory by default" in section
    assert "Heavy services must be explicit" in section
    assert "Secrets must come from environment variables" in section


def test_isolated_product_system_mode_requires_real_isolation_surfaces() -> None:
    text = DOC.read_text(encoding="utf-8")
    section = _section(text, "## Isolated Product-System Mode")
    rows = _table_rows(section)
    requirements = {row[0]: row[1] for row in rows[1:]}

    assert "disposable git worktree" in requirements["Repository"]
    assert ".cognitive-os/" in requirements["Runtime state"]
    assert "Docker Compose project names" in requirements["Service state"]
    assert "never connect to production data" in requirements["Data"]
    assert "Temporary/canary installs must not enter" in requirements["Registry"]


def test_product_system_connection_contract_requires_happy_path_and_boundary() -> None:
    text = DOC.read_text(encoding="utf-8")
    section = _section(text, "## Isolated Product-System Mode")

    ordered_terms = [
        "required tools and Python groups",
        "required optional services",
        "readiness checks and teardown behavior",
        "which artifacts prove success",
        "degraded behavior",
    ]
    positions = [section.index(term) for term in ordered_terms]
    assert positions == sorted(positions)
    assert "happy path" in section
    assert "isolation boundary" in section
    assert "without leaking host paths, credentials, or temporary installs" in section


def test_manual_proof_path_runs_dependency_doctor_services_and_summary_in_order() -> None:
    import re

    text = DOC.read_text(encoding="utf-8")
    section = _section(text, "## Manual Proof Path")
    commands = "\n".join(_commands(section))

    assert commands.index("bash scripts/manifest-check.sh --profile default") < commands.index(
        "bash scripts/setup.sh --standard"
    )
    assert commands.index("bash scripts/setup.sh --standard") < commands.index(
        "bash scripts/cos-doctor-tools.sh"
    )
    # Accepts both legacy wrapper and new cos-test entry during deprecation cycle (ADR-072).
    canonical_pattern = re.compile(
        r"bash scripts/pytest-with-summary\.sh|cos-test cluster|cos-test broad"
    )
    canonical_match = canonical_pattern.search(commands)
    assert canonical_match is not None, (
        "Manual Proof Path must reference either 'bash scripts/pytest-with-summary.sh', "
        "'cos-test cluster', or 'cos-test broad' as the final test step"
    )
    bootstrap_pos = commands.index("bash scripts/cos-bootstrap.sh --profile full")
    assert bootstrap_pos < canonical_match.start(), (
        "cos-bootstrap.sh must appear before the canonical test command in Manual Proof Path"
    )


def test_local_connected_systems_validation_is_linked_from_entrypoints() -> None:
    docs_readme = (PROJECT_ROOT / "docs" / "README.md").read_text(encoding="utf-8")
    runtime_plan = (
        PROJECT_ROOT / ".cognitive-os" / "plans" / "architecture" / "headless-clustered-runtime-plan.md"
    ).read_text(encoding="utf-8")
    checklist = (PROJECT_ROOT / "docs" / "business" / "master-plan-checklist.md").read_text(
        encoding="utf-8"
    )

    assert docs_readme.count("manual-tests/local-connected-systems-validation.md") == 1
    assert runtime_plan.count("manual-tests/local-connected-systems-validation.md") == 2
    assert checklist.count("manual-tests/local-connected-systems-validation.md") == 1
