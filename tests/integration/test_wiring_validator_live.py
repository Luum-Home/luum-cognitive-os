"""Integration tests for WiringValidator against the real luum-agent-os repo."""
from pathlib import Path

import pytest

from lib.wiring_validator import WiringValidator


@pytest.fixture(scope="module")
def validator() -> WiringValidator:
    project_root = Path(__file__).resolve().parent.parent.parent
    return WiringValidator(str(project_root))


class TestLiveWiringValidator:
    def test_live_validate_all_hooks(self, validator: WiringValidator) -> None:
        results = validator.validate_all_hooks()
        assert len(results) > 10, "Expected at least 10 hooks in the real repo"
        for r in results:
            assert "wiring_score" in r
            assert 0.0 <= r["wiring_score"] <= 1.0
            assert "name" in r
            # Internal helpers must not appear
            assert not r["name"].startswith("_")

    def test_live_validate_all_libs(self, validator: WiringValidator) -> None:
        results = validator.validate_all_libs()
        assert len(results) > 20, "Expected at least 20 lib modules"
        for r in results:
            assert "wiring_score" in r
            assert "imported_by" in r
            assert isinstance(r["imported_by"], list)

    def test_live_unwired_components(self, validator: WiringValidator) -> None:
        result = validator.get_unwired_components()
        assert "total_unwired" in result
        assert isinstance(result["total_unwired"], int)
        # There will always be some unwired components in this repo
        print(
            f"\nUnwired: {result['total_unwired']} total "
            f"({len(result['hooks'])} hooks, {len(result['libs'])} libs, "
            f"{len(result['rules'])} rules)"
        )

    def test_live_format_report(self, validator: WiringValidator) -> None:
        report = validator.format_wiring_report()
        assert "WIRING REPORT" in report
        assert "HOOKS:" in report
        assert "LIBS:" in report
        assert "RULES:" in report
        assert len(report) > 100, "Report should be non-trivial"
        print(f"\n{report[:800]}")

    def test_live_format_fix_commands(self, validator: WiringValidator) -> None:
        fixes = validator.format_fix_commands()
        assert "FIX COMMANDS" in fixes
        assert "set-security-profile" in fixes
