"""Audit tests for Phoenix license and installation boundary."""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_phoenix_server_stays_out_of_core_lock_and_pyproject() -> None:
    """ELv2 Phoenix server must remain an explicit heavy lane, not bundled core."""
    pyproject = _read("pyproject.toml")
    lock = _read("uv.lock")
    lane = _read("requirements/dependency-lanes/observability.txt")

    assert "arize-phoenix" not in pyproject
    assert 'name = "arize-phoenix"' not in lock
    assert "arize-phoenix>=4.0" in lane


def test_key_phoenix_docs_state_elv2_boundary() -> None:
    key_docs = [
        "docs/adrs/ADR-058-observability-migration-langfuse-to-phoenix.md",
        "docs/architecture/infrastructure-service-catalog.md",
        "cognitive-os.yaml",
        "NOTICE",
        "skills/phoenix-trace-ui/SKILL.md",
    ]

    for path in key_docs:
        text = _read(path)
        assert "ELv2" in text or "Elastic License 2.0" in text, f"{path} must state Phoenix ELv2 boundary"


def test_active_phoenix_docs_do_not_reference_removed_pyproject_extra_install() -> None:
    active_docs = [
        "CHANGELOG.md",
        "docs/INDEX.md",
        "docs/getting-started.md",
        "docs/adrs/ADR-170-operator-cli-as-primary-ui-surface.md",
        "docs/adrs/ADR-172-multi-surface-ui-architecture.md",
        "skills/phoenix-trace-ui/SKILL.md",
    ]

    for path in active_docs:
        text = _read(path)
        assert "uv sync --extra observability" not in text
        assert "[project.optional-dependencies] observability" not in text
        assert "pyproject.toml` observability" not in text
