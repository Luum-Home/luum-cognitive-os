from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
INTEGRATION_DIR = PROJECT_ROOT / "tests" / "integration"


def _integration_test_files() -> list[Path]:
    return sorted(INTEGRATION_DIR.glob("test*.py"))


def test_testcontainer_lanes_are_explicitly_opt_in() -> None:
    """Heavy testcontainers lanes must not run in the default suite by accident."""
    offenders: list[str] = []
    container_tokens = (
        "DockerContainer(",
        "PostgresContainer(",
        "MySqlContainer(",
    )

    for path in _integration_test_files():
        text = path.read_text(errors="replace")
        if not any(token in text for token in container_tokens):
            continue
        if "COS_RUN_" not in text:
            offenders.append(str(path.relative_to(PROJECT_ROOT)))

    assert not offenders, (
        "Integration tests that create testcontainers must be behind an explicit "
        "COS_RUN_* opt-in flag so default repair lanes do not start Docker stacks:\n"
        + "\n".join(f"- {offender}" for offender in offenders)
    )


def test_optional_docker_lane_flags_are_documented() -> None:
    """Every COS_RUN_* gate in integration tests should appear in docs/09-Quality/root/testing.md."""
    docs = (PROJECT_ROOT / "docs" / "09-Quality" / "root" / "testing.md").read_text(errors="replace")
    missing: list[str] = []

    for path in _integration_test_files():
        text = path.read_text(errors="replace")
        for token in sorted(set(part for part in text.split() if part.startswith("COS_RUN_"))):
            flag = token.strip("`'\"),.:;")
            if flag and flag not in docs:
                missing.append(f"{path.relative_to(PROJECT_ROOT)}: {flag}")

    assert not missing, (
        "Optional Docker lane flags must be documented in docs/09-Quality/root/testing.md:\n"
        + "\n".join(f"- {entry}" for entry in missing)
    )
